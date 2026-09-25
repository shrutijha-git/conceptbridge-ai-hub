from decimal import Decimal, InvalidOperation
import csv, io, re
from collections import defaultdict
from datetime import datetime

QUESTIONS = {
 'buyer-power': {'mode':'understand','concept':'Buyer vs supplier power','prompt':'A supermarket buys 60% of a bakery’s output and demands a discount. Which force is most directly affecting the bakery?','options':['Buyer power','Supplier power','Threat of substitutes','New entrants'],'answer':'Buyer power','explanation':'The supermarket buys the bakery’s output. Its purchase volume gives it buyer power.','hint':'Who buys the focal business’s output?','next':'supplier-power'},
 'supplier-power': {'mode':'understand','concept':'Buyer vs supplier power','prompt':'A bakery relies on the only mill that can supply special flour. Switching is expensive. Which force does the mill have?','options':['Buyer power','Supplier power','Threat of substitutes','New entrants'],'answer':'Supplier power','explanation':'The mill supplies an input with few alternatives. Switching costs strengthen supplier power.','hint':'Who provides an input to the bakery?','next':'buyer-power'},
 '3nf': {'mode':'understand','concept':'Transitive dependency','prompt':'In Student(StudentID, DeptID, DeptName), StudentID is the sole candidate key. StudentID determines DeptID; DeptID determines DeptName. Which dependency of DeptName on StudentID is illustrated?','options':['Transitive dependency','Partial dependency','No dependency'],'answer':'Transitive dependency','explanation':'DeptName depends on StudentID through DeptID. Given the stated sole candidate key, DeptName is a non-prime attribute and DeptID is not a superkey.','hint':'Follow the two-step dependency path.','next':'3nf-decompose'},
 '3nf-decompose': {'mode':'understand','concept':'Transitive dependency','prompt':'For Student(StudentID, DeptID, DeptName), under the stated dependencies StudentID → DeptID and DeptID → DeptName, choose the decomposition that removes the transitive dependency.','options':['Student(StudentID, DeptID) + Department(DeptID, DeptName)','Student(StudentID, DeptName) only'],'answer':'Student(StudentID, DeptID) + Department(DeptID, DeptName)','explanation':'Store the department name with DeptID in Department; Student retains the department reference.','hint':'Which attribute determines DeptName directly?','next':'3nf'},
 'margin-1': {'mode':'practise','concept':'Profit margin','prompt':'Revenue is 250000 and total cost is 200000. Calculate profit margin as a percentage. Enter the number without %.','answer':'20','explanation':'Profit margin = (Revenue − Cost) / Revenue × 100 = 50000 / 250000 × 100 = 20%.','hint':'Use revenue as the denominator, not cost.','next':'margin-2'},
 'margin-2': {'mode':'practise','concept':'Profit margin','prompt':'Revenue is 180000 and total cost is 135000. Calculate profit margin as a percentage. Enter the number without %.','answer':'25','explanation':'Profit is 45000. Profit margin = 45000 / 180000 × 100 = 25%.','hint':'Divide profit by revenue, then multiply by 100.','next':'margin-1'},
 'python-distinct': {'mode':'code','concept':'Distinct values','prompt':'Write second_largest(numbers). Return the second-largest distinct value, or None if fewer than two distinct values exist.','hint':'Trace [5, 5, 3], [], and [7].','next':'python-top-k'},
 'python-top-k': {'mode':'code','concept':'Distinct values','prompt':'Write top_k_distinct(numbers,k), returning up to k distinct values in descending order. Return [] for k <= 0.','hint':'Deduplicate first and consider non-positive k.','next':'python-distinct'},
 'sql-groups': {'mode':'code','concept':'SQL aggregation','prompt':'Table sales(region TEXT, amount REAL). Return total sales per region, only where SUM(amount) > 10000. Use SQLite-compatible or standard SQL.','hint':'WHERE filters rows; HAVING filters grouped results.','next':'sql-averages'},
 'sql-averages': {'mode':'code','concept':'SQL aggregation','prompt':'Table sales(region TEXT, amount REAL). Return regions with at least three records and their average sale.','hint':'Group by region and filter with HAVING COUNT(*) >= 3.','next':'sql-groups'},
}

def public_question(key):
    q=QUESTIONS[key]
    return {'id':key,**{k:v for k,v in q.items() if k not in {'answer','explanation','next'}}}

def assess(key, answer):
    if key not in QUESTIONS: raise ValueError('Unknown practice question')
    q=QUESTIONS[key]
    if q['mode']=='code':
        code=re.sub(r'#[^\n]*|--[^\n]*','',answer)
        issues=[]
        if key.startswith('python'):
            if re.search(r'\bpass\b',code) or 'return' not in code: issues.append('The implementation still needs a return value.')
            if re.search(r'sorted\(\s*numbers\s*[,)]',code) and not re.search(r'set\s*\(|not\s+in',code): issues.append('Sorting the original list may leave duplicates. Trace the duplicate-value example.')
            if key=='python-distinct' and '[-2]' in code and not re.search(r'len\s*\(|except|\bif\b',code): issues.append('Guard against fewer than two distinct values before indexing.')
        else:
            before_group=re.split(r'GROUP\s+BY',code,flags=re.I)[0]
            if re.search(r'WHERE.*(?:SUM|AVG|COUNT)\s*\(',before_group,re.I|re.S): issues.append('Move a grouped aggregate condition from WHERE to HAVING.')
            if not re.search(r'GROUP\s+BY\s+region',code,re.I): issues.append('Check that results are grouped by region.')
        return {'correct':None,'verdict':'needs-practice' if issues else 'reviewed','explanation':' '.join(issues) or 'No built-in mistake pattern was detected. This is not a correctness check. Run your own tests.', 'method':'static_review_cues','code_executed':False,'hint':q['hint'],'follow_up':public_question(q['next'])}
    if key.startswith('margin'):
        try: correct=abs(Decimal(answer.strip().rstrip('%'))-Decimal(q['answer']))<=Decimal('0.01')
        except InvalidOperation: correct=False
    else: correct=answer.strip().casefold()==q['answer'].casefold()
    return {'correct':correct,'verdict':'on-track' if correct else 'needs-practice','explanation':q['explanation'],'method':'calculated_answer' if key.startswith('margin') else 'built_in_answer_key','hint':q['hint'],'follow_up':public_question(q['next'])}

def analyze_sales(text, date_column='date', value_column='sales', category_column='region'):
    if len(text.encode())>2_000_000: raise ValueError('Use a CSV no larger than 2 MB.')
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')),strict=True)
    headers=reader.fieldnames or []
    if len(headers)!=len(set(headers)) or not all(headers): raise ValueError('Use unique non-empty column names.')
    if date_column not in headers or value_column not in headers or category_column not in headers: raise ValueError('The selected columns do not exist in this dataset.')
    monthly=defaultdict(Decimal);categories=defaultdict(Decimal);excluded=0;count=0
    for count,row in enumerate(reader,1):
        if count>10000: raise ValueError('Use up to 10,000 rows.')
        if None in row or any(v is None for v in row.values()): raise ValueError(f'Row {count+1} does not match the header width.')
        try:
            value=row[value_column].strip()
            if not re.fullmatch(r'[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?',value): raise ValueError()
            amount=Decimal(value.replace(',',''))
            raw_date=row[date_column].strip()
            if not re.fullmatch(r'\d{4}-\d{2}(?:-\d{2})?',raw_date): raise ValueError()
            date=datetime.strptime(raw_date,'%Y-%m-%d' if len(raw_date)==10 else '%Y-%m')
            category=row[category_column].strip()
            if not category: raise ValueError()
        except (ValueError,InvalidOperation):
            excluded+=1;continue
        monthly[date.strftime('%Y-%m')]+=amount;categories[category]+=amount
    if not monthly: raise ValueError('No usable rows. Check dates, numeric values and categories.')
    return {'rows':count,'excluded_rows':excluded,'monthly_totals':[{'month':k,'total':str(v)} for k,v in sorted(monthly.items())],
            'category_totals':[{'category':k,'total':str(v)} for k,v in sorted(categories.items())],
            'total':str(sum(monthly.values(),Decimal(0))),'method':'Python Decimal arithmetic','missing_months':'unknown, not assumed zero'}
