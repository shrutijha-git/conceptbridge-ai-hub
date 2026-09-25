"use client";

import { useState } from "react";
import {
  CheckCircle2,
  CircleAlert,
  RotateCcw,
  Trophy,
} from "lucide-react";

import { api, errorText, postJson } from "@/lib/api";

import { BusyLabel, ErrorBox } from "./ui";


type PracticeQuestion = {
  id: string;
  question: string;
  options: string[];
};


type PracticeTest = {
  test_id: string;
  degree: string;
  subject: string;
  topic: string;
  difficulty: string;
  total_questions: number;
  questions: PracticeQuestion[];
};


type ReviewItem = {
  id: string;
  question: string;
  options: string[];
  your_answer: string;
  correct_answer: string;
  correct: boolean;
  explanation: string;
};


type PracticeResult = {
  test_id: string;
  degree: string;
  subject: string;
  topic: string;
  difficulty: string;
  total_questions: number;
  answered: number;
  score: number;
  percentage: number;
  review: ReviewItem[];
};


export function PracticeTestPanel({
  sessionId,
  locked,
  begin,
  finish,
}: {
  sessionId: string;
  locked: boolean;
  begin: (name: string) => void;
  finish: () => void;
}) {

  const [degree, setDegree] = useState("");
  const [subject, setSubject] = useState("");
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("Medium");

  const [test, setTest] =
    useState<PracticeTest | null>(null);

  const [answers, setAnswers] =
    useState<Record<string, string>>({});

  const [result, setResult] =
    useState<PracticeResult | null>(null);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] =
    useState(false);

  const [error, setError] = useState("");


  // ==========================================================
  // GENERATE TEST
  // ==========================================================

  async function generateTest() {

    const finalDegree = degree.trim();
    const finalSubject = subject.trim();
    const finalTopic = topic.trim();

    if (!finalDegree) {
      setError("Enter a degree.");
      return;
    }

    if (!finalSubject) {
      setError("Enter a subject.");
      return;
    }

    if (!finalTopic) {
      setError("Enter a topic.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setTest(null);
    setAnswers({});

    begin("practice-test");

    try {

      const generated =
        await postJson<PracticeTest>(
          "/practice-tests/generate",
          {
            degree: finalDegree,
            subject: finalSubject,
            topic: finalTopic,
            difficulty,
          },
        );

      setTest(generated);

    } catch (err) {

      setError(errorText(err));

    } finally {

      setLoading(false);
      finish();

    }
  }


  // ==========================================================
  // SELECT ANSWER
  // ==========================================================

  function selectAnswer(
    questionId: string,
    answer: string,
  ) {

    if (result) return;

    setAnswers((current) => ({
      ...current,
      [questionId]: answer,
    }));
  }


  // ==========================================================
  // SUBMIT
  // ==========================================================

  async function submitTest() {

    if (!test || result) return;

    const unanswered =
      test.questions.filter(
        (question) =>
          !answers[question.id],
      ).length;

    if (unanswered > 0) {

      const confirmed = window.confirm(
        `You have ${unanswered} unanswered question${
          unanswered === 1 ? "" : "s"
        }. Submit anyway?`,
      );

      if (!confirmed) return;
    }

    setSubmitting(true);
    setError("");

    begin("practice-test-submit");

    try {

      const response =
        await postJson<PracticeResult>(
          "/practice-tests/submit",
          {
            test_id: test.test_id,
            answers,
          },
        );

      setResult(response);

    } catch (err) {

      setError(errorText(err));

    } finally {

      setSubmitting(false);
      finish();

    }
  }


  // ==========================================================
  // START AGAIN
  // ==========================================================

  function startAgain() {

    setTest(null);
    setResult(null);
    setAnswers({});
    setError("");

  }


  // ==========================================================
  // RESULT SCREEN
  // ==========================================================

  if (result) {

    return (
      <section className="content-card practice-test-card">

        <div className="section-heading">

          <div>
            <span className="eyebrow">
              TEST COMPLETE
            </span>

            <h2>
              Your practice result
            </h2>
          </div>

          <Trophy size={30} />

        </div>


        <div className="practice-result-summary">

          <div className="practice-score-circle">

            <strong>
              {result.score}
            </strong>

            <span>
              / {result.total_questions}
            </span>

          </div>

          <div>

            <h3>
              {result.percentage}%
            </h3>

            <p className="muted">
              {result.answered} of{" "}
              {result.total_questions} questions
              answered
            </p>

            <p className="muted">
              {result.degree} ·{" "}
              {result.subject} ·{" "}
              {result.topic}
            </p>

          </div>

        </div>


        <div className="practice-review">

          <div className="section-heading">

            <div>
              <span className="eyebrow">
                REVIEW
              </span>

              <h3>
                Review your answers
              </h3>
            </div>

          </div>


          {result.review.map(
            (item, index) => (

              <article
                key={item.id}
                className={`practice-review-item ${
                  item.correct
                    ? "is-correct"
                    : "is-incorrect"
                }`}
              >

                <div className="practice-review-heading">

                  {item.correct ? (
                    <CheckCircle2 size={20} />
                  ) : (
                    <CircleAlert size={20} />
                  )}

                  <strong>
                    Question {index + 1}
                  </strong>

                </div>


                <h4>
                  {item.question}
                </h4>


                <p>
                  <strong>
                    Your answer:
                  </strong>{" "}
                  {item.your_answer ||
                    "Not answered"}
                </p>


                {!item.correct && (
                  <p>
                    <strong>
                      Correct answer:
                    </strong>{" "}
                    {item.correct_answer}
                  </p>
                )}


                <div className="practice-explanation">

                  <strong>
                    Explanation
                  </strong>

                  <p>
                    {item.explanation}
                  </p>

                </div>

              </article>

            ),
          )}

        </div>


        <button
          className="primary"
          type="button"
          onClick={startAgain}
        >
          <RotateCcw size={17} />
          Take another test
        </button>

      </section>
    );
  }


  // ==========================================================
  // TEST SCREEN
  // ==========================================================

  if (test) {

    const answered =
      Object.keys(answers).length;

    return (
      <section className="content-card practice-test-card">

        <div className="section-heading">

          <div>

            <span className="eyebrow">
              PRACTICE TEST
            </span>

            <h2>
              {test.topic}
            </h2>

            <p className="muted">
              {test.degree} ·{" "}
              {test.subject} ·{" "}
              {test.difficulty}
            </p>

          </div>

          <span className="tag">
            {answered}/15 answered
          </span>

        </div>


        <div className="practice-test-instruction">
          Answer all 15 questions before submitting.
          Answers and explanations are hidden until
          you submit the test.
        </div>


        <div className="practice-test-questions">

          {test.questions.map(
            (question, index) => (

              <article
                key={question.id}
                className="practice-test-question"
              >

                <div className="practice-question-number">
                  Question {index + 1} of 15
                </div>

                <h3>
                  {question.question}
                </h3>


                <div className="practice-test-options">

                  {question.options.map(
                    (option, optionIndex) => {

                      const selected =
                        answers[question.id] ===
                        option;

                      return (
                        <label
                          key={option}
                          className={
                            selected
                              ? "selected"
                              : ""
                          }
                        >

                          <input
                            type="radio"
                            name={
                              `question-${question.id}`
                            }
                            checked={selected}
                            disabled={
                              locked ||
                              submitting
                            }
                            onChange={() =>
                              selectAnswer(
                                question.id,
                                option,
                              )
                            }
                          />

                          <span className="option-letter">
                            {String.fromCharCode(
                              65 + optionIndex,
                            )}
                          </span>

                          <span>
                            {option}
                          </span>

                        </label>
                      );
                    },
                  )}

                </div>

              </article>

            ),
          )}

        </div>


        <div className="practice-submit-bar">

          <div>

            <strong>
              {answered}/15 answered
            </strong>

            <span className="muted">
              You can submit even if some are unanswered.
            </span>

          </div>

          <button
            className="primary"
            type="button"
            disabled={
              locked ||
              submitting
            }
            onClick={() =>
              void submitTest()
            }
          >
            {submitting ? (
              <BusyLabel text="Submitting test…" />
            ) : (
              "Submit Test"
            )}
          </button>

        </div>


        <ErrorBox text={error} />

      </section>
    );
  }


  // ==========================================================
  // SETUP SCREEN
  // ==========================================================

  return (
    <section className="content-card practice-test-card">

      <div className="section-heading">

        <div>

          <span className="eyebrow">
            PRACTICE TEST
          </span>

          <h2>
            Test yourself with 15 questions.
          </h2>

          <p className="muted">
            Choose your academic context and
            ConceptBridge will generate a fresh
            15-question test using AI.
          </p>

        </div>

      </div>


      <div className="practice-test-form">

        <label>
          Degree

          <input
            value={degree}
            disabled={loading}
            onChange={(event) =>
              setDegree(event.target.value)
            }
            placeholder="e.g. MCA"
            maxLength={150}
          />

          <small className="muted">
            Enter any degree, including one not
            listed in the curriculum.
          </small>

        </label>


        <label>
          Subject

          <input
            value={subject}
            disabled={loading}
            onChange={(event) =>
              setSubject(event.target.value)
            }
            placeholder="e.g. DBMS"
            maxLength={150}
          />
        </label>


        <label>
          Topic

          <input
            value={topic}
            disabled={loading}
            onChange={(event) =>
              setTopic(event.target.value)
            }
            placeholder="e.g. Normalization"
            maxLength={255}
          />
        </label>


        <label>
          Difficulty

          <select
            value={difficulty}
            disabled={loading}
            onChange={(event) =>
              setDifficulty(
                event.target.value,
              )
            }
          >
            <option value="Easy">
              Easy
            </option>

            <option value="Medium">
              Medium
            </option>

            <option value="Hard">
              Hard
            </option>
          </select>
        </label>


        <ErrorBox text={error} />


        <button
          className="primary"
          type="button"
          disabled={
            loading ||
            !degree.trim() ||
            !subject.trim() ||
            !topic.trim()
          }
          onClick={() =>
            void generateTest()
          }
        >
          {loading ? (
            <BusyLabel text="Generating 15 questions…" />
          ) : (
            "Generate 15 Questions"
          )}
        </button>

      </div>

    </section>
  );
}