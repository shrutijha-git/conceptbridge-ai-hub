"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  Code2,
  Lightbulb,
  Play,
  RotateCcw,
} from "lucide-react";

import { postJson } from "@/lib/api";

type Challenge = {
  challenge_id: string;
  degree: string;
  subject: string;
  topic: string;
  language: string;
  title: string;
  description: string;
  requirements: string[];
  example_input: string;
  example_output: string;
  starter_code: string;
  hints: string[];
};

type Evaluation = {
  score: number;
  correct: boolean;
  summary: string;
  strengths: string[];
  issues: string[];
  suggestions: string[];
  explanation: string;
};

export function CodePracticePanel({
  degree: initialDegree,
  subject: initialSubject,
  topic: initialTopic,
  locked,
}: {
  degree?: string;
  subject?: string;
  topic?: string;
  locked: boolean;
}) {
  const [degree, setDegree] = useState(
    initialDegree?.trim() || "",
  );

  const [subject, setSubject] = useState(
    initialSubject?.trim() || "",
  );

  const [topic, setTopic] = useState(
    initialTopic?.trim() || "",
  );

  const [language, setLanguage] =
    useState("Python");

  const [customLanguage, setCustomLanguage] =
    useState("");

  const [challenge, setChallenge] =
    useState<Challenge | null>(null);

  const [code, setCode] =
    useState("");

  const [evaluation, setEvaluation] =
    useState<Evaluation | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [submitting, setSubmitting] =
    useState(false);

  const [error, setError] =
    useState("");

  useEffect(() => {
    setDegree(initialDegree?.trim() || "");
    setSubject(initialSubject?.trim() || "");
    setTopic(initialTopic?.trim() || "");
  }, [
    initialDegree,
    initialSubject,
    initialTopic,
  ]);

  async function generateChallenge() {
    const finalDegree = degree.trim();
    const finalSubject = subject.trim();
    const finalTopic = topic.trim();

    const finalLanguage =
      language === "Other"
        ? customLanguage.trim()
        : language;

    if (!finalDegree) {
      setError("Please enter your degree.");
      return;
    }

    if (!finalSubject) {
      setError("Please enter your subject.");
      return;
    }

    if (!finalTopic) {
      setError("Please enter your topic.");
      return;
    }

    if (!finalLanguage) {
      setError(
        "Please enter your programming language.",
      );
      return;
    }

    setLoading(true);
    setError("");
    setEvaluation(null);

    try {
      const result =
        await postJson<Challenge>(
          "/code-practice/generate",
          {
            degree: finalDegree,
            subject: finalSubject,
            topic: finalTopic,
            language: finalLanguage,
          },
        );

      setChallenge(result);
      setCode(result.starter_code);

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to generate coding challenge.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function submitSolution() {
    if (
      locked ||
      !challenge ||
      !code.trim()
    ) {
      return;
    }

    setSubmitting(true);
    setError("");
    setEvaluation(null);

    try {
      const result =
        await postJson<Evaluation>(
          "/code-practice/submit",
          {
            challenge_id:
              challenge.challenge_id,
            code,
          },
        );

      setEvaluation(result);

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to evaluate your solution.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="workspace-card code-practice-panel">

      <div className="section-heading">
        <div>
          <span className="eyebrow">
            CODE PRACTICE
          </span>

          <h2>
            Solve a problem with code.
          </h2>

          <p>
            ConceptBridge will generate a
            coding challenge for your academic
            context.
          </p>
        </div>

        <Code2 size={28} />
      </div>

      {/* =====================================================
          ACADEMIC CONTEXT
          ===================================================== */}

      <div className="code-context-form">

        <label>
          Degree

          <input
            type="text"
            value={degree}
            onChange={(event) =>
              setDegree(event.target.value)
            }
            placeholder="e.g. MCA"
            disabled={
              loading || submitting
            }
          />

          <small>
            Enter your degree. You can use any
            degree, including one not listed.
          </small>
        </label>

        <label>
          Subject

          <input
            type="text"
            value={subject}
            onChange={(event) =>
              setSubject(event.target.value)
            }
            placeholder="e.g. DBMS"
            disabled={
              loading || submitting
            }
          />
        </label>

        <label>
          Topic

          <input
            type="text"
            value={topic}
            onChange={(event) =>
              setTopic(event.target.value)
            }
            placeholder="e.g. Normalization"
            disabled={
              loading || submitting
            }
          />
        </label>

      </div>

      {/* =====================================================
          LANGUAGE
          ===================================================== */}

      <div className="code-controls">

        <label>
          Programming language

          <select
            value={language}
            onChange={(event) => {
              setLanguage(event.target.value);

              if (
                event.target.value !== "Other"
              ) {
                setCustomLanguage("");
              }
            }}
            disabled={
              loading || submitting
            }
          >
            <option value="Python">
              Python
            </option>

            <option value="Java">
              Java
            </option>

            <option value="JavaScript">
              JavaScript
            </option>

            <option value="C++">
              C++
            </option>

            <option value="C">
              C
            </option>

            <option value="SQL">
              SQL
            </option>

            <option value="R">
              R
            </option>

            <option value="PHP">
              PHP
            </option>

            <option value="Go">
              Go
            </option>

            <option value="Rust">
              Rust
            </option>

            <option value="Other">
              Other
            </option>
          </select>
        </label>

        {language === "Other" && (
          <label>
            Enter programming language

            <input
              type="text"
              value={customLanguage}
              onChange={(event) =>
                setCustomLanguage(
                  event.target.value,
                )
              }
              placeholder="e.g. Kotlin"
              disabled={
                loading || submitting
              }
            />
          </label>
        )}

        <button
          className="primary"
          type="button"
          onClick={() =>
            void generateChallenge()
          }
          disabled={
            locked ||
            loading ||
            submitting
          }
        >
          {loading
            ? "Generating..."
            : challenge
              ? "New Challenge"
              : "Generate Challenge"}
        </button>

      </div>

      {/* =====================================================
          ERROR
          ===================================================== */}

      {error && (
        <div className="error-box">
          {error}
        </div>
      )}

      {/* =====================================================
          CHALLENGE
          ===================================================== */}

      {challenge && (
        <>

          <article className="code-challenge">

            <div className="code-challenge-header">

              <div>
                <span className="eyebrow">
                  AI CHALLENGE
                </span>

                <h3>
                  {challenge.title}
                </h3>
              </div>

              <span className="code-language">
                {challenge.language}
              </span>

            </div>

            <p className="code-description">
              {challenge.description}
            </p>

            <div className="code-requirements">

              <h4>
                Requirements
              </h4>

              <ul>
                {challenge.requirements.map(
                  (item, index) => (
                    <li key={index}>
                      {item}
                    </li>
                  ),
                )}
              </ul>

            </div>

            <div className="code-examples">

              <div>
                <strong>
                  Example input
                </strong>

                <pre>
                  {challenge.example_input}
                </pre>
              </div>

              <div>
                <strong>
                  Example output
                </strong>

                <pre>
                  {challenge.example_output}
                </pre>
              </div>

            </div>

          </article>

          {/* =================================================
              CODE EDITOR
              ================================================= */}

          <div className="code-editor-card">

            <div className="code-editor-header">

              <span>
                Your solution
              </span>

              <span>
                {challenge.language}
              </span>

            </div>

            <textarea
              className="code-editor"
              value={code}
              onChange={(event) =>
                setCode(event.target.value)
              }
              spellCheck={false}
              disabled={
                locked ||
                submitting
              }
              placeholder="Write your solution here..."
            />

            <div className="code-actions">

              <button
                type="button"
                className="secondary"
                onClick={() =>
                  setCode(
                    challenge.starter_code,
                  )
                }
                disabled={submitting}
              >
                <RotateCcw size={16} />
                Reset
              </button>

              <button
                type="button"
                className="primary"
                onClick={() =>
                  void submitSolution()
                }
                disabled={
                  locked ||
                  submitting ||
                  !code.trim()
                }
              >
                <Play size={16} />

                {submitting
                  ? "Evaluating..."
                  : "Submit Solution"}
              </button>

            </div>

          </div>

          {/* =================================================
              HINTS
              ================================================= */}

          {challenge.hints.length > 0 && (
            <details className="code-hints">

              <summary>
                <Lightbulb size={17} />
                Need a hint?
              </summary>

              <ul>
                {challenge.hints.map(
                  (hint, index) => (
                    <li key={index}>
                      {hint}
                    </li>
                  ),
                )}
              </ul>

            </details>
          )}

          {/* =================================================
              EVALUATION
              ================================================= */}

          {evaluation && (
            <article className="code-evaluation">

              <div className="evaluation-score">

                <CheckCircle2 size={26} />

                <div>
                  <span>
                    AI evaluation
                  </span>

                  <strong>
                    {evaluation.score}/100
                  </strong>
                </div>

              </div>

              <h3>
                {evaluation.summary}
              </h3>

              <p>
                {evaluation.explanation}
              </p>

              {evaluation.strengths.length > 0 && (
                <div>
                  <h4>
                    What you did well
                  </h4>

                  <ul>
                    {evaluation.strengths.map(
                      (item, index) => (
                        <li key={index}>
                          {item}
                        </li>
                      ),
                    )}
                  </ul>
                </div>
              )}

              {evaluation.issues.length > 0 && (
                <div>
                  <h4>
                    What needs improvement
                  </h4>

                  <ul>
                    {evaluation.issues.map(
                      (item, index) => (
                        <li key={index}>
                          {item}
                        </li>
                      ),
                    )}
                  </ul>
                </div>
              )}

              {evaluation.suggestions.length > 0 && (
                <div>
                  <h4>
                    Suggestions
                  </h4>

                  <ul>
                    {evaluation.suggestions.map(
                      (item, index) => (
                        <li key={index}>
                          {item}
                        </li>
                      ),
                    )}
                  </ul>
                </div>
              )}

            </article>
          )}

        </>
      )}

    </section>
  );
}