"use client";

import { useEffect, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Code2,
  Lightbulb,
  Target,
} from "lucide-react";

import { api, errorText, postJson } from "@/lib/api";

import type {
  Feedback,
  Memory,
  Mode,
  Progress,
  Question,
} from "@/lib/types";

import { BusyLabel, ErrorBox } from "./ui";

export function PracticePanel({
  mode,
  sessionId,
  initialQuestionId,
  locked,
  begin,
  finish,
  onSaved,
  askTutor,
}: {
  mode: Mode;
  sessionId: string;
  initialQuestionId: string;
  locked: boolean;
  begin: (name: string) => void;
  finish: () => void;
  onSaved: () => Promise<void>;
  askTutor: (text: string) => void;
}) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [questionId, setQuestionId] = useState("");
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [reload, setReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);
    setError("");

    api<Question[]>(
      `/practice/questions?mode=${mode}`,
      {
        signal: controller.signal,
      },
    )
      .then((rows) => {
        if (controller.signal.aborted) {
          return;
        }

        setQuestions(rows);

        const initial =
          rows.find(
            (question) =>
              question.id === initialQuestionId,
          ) ||
          rows.find(
            (question) => question.id === "3nf",
          ) ||
          rows[0];

        setQuestionId(initial?.id || "");
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setError(errorText(err));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [mode, reload, initialQuestionId]);

  const question = questions.find(
    (item) => item.id === questionId,
  );

  function changeQuestion(id: string) {
    setQuestionId(id);
    setAnswer("");
    setFeedback(null);
    setError("");
    setNotice("");
  }

  async function submit() {
    if (
      locked ||
      !question ||
      !answer.trim()
    ) {
      return;
    }

    begin("practice");

    setSubmitting(true);
    setError("");
    setFeedback(null);
    setNotice("");

    let saved = false;

    try {
      const result =
        await postJson<{ feedback: Feedback }>(
          "/practice/attempts",
          {
            session_id: sessionId,
            question_id: question.id,
            answer: answer.trim(),
          },
        );

      saved = true;

      setFeedback(result.feedback);

      await onSaved();
    } catch (err) {
      if (saved) {
        setNotice(
          "Your attempt was saved. Reopen the session to refresh its learning record.",
        );
      } else {
        setError(errorText(err));
      }
    } finally {
      setSubmitting(false);
      finish();
    }
  }

  return (
    <section className="content-card practice-card">
      <div className="section-heading">
        <span className="eyebrow">
          LEARN BY DOING
        </span>

        <span className="tag">
          {mode === "code"
            ? "Code review"
            : mode === "practise"
              ? "Numerical practice"
              : "Concept check"}
        </span>
      </div>

      <h2>Make an attempt.</h2>

      <p className="muted">
        Get feedback, understand a mistake, and try
        a related question.
      </p>

      {loading ? (
        <div className="loading-panel">
          <BusyLabel text="Loading questions…" />
        </div>
      ) : (
        <>
          <label className="question-picker">
            Choose a question

            <select
              value={questionId}
              onChange={(event) =>
                changeQuestion(
                  event.target.value,
                )
              }
              disabled={locked}
            >
              {questions.map((item) => (
                <option
                  key={item.id}
                  value={item.id}
                >
                  {item.concept} — {item.id}
                </option>
              ))}
            </select>
          </label>

          {question && (
            <>
              <div className="question-block">
                <span className="small-icon">
                  {mode === "code" ? (
                    <Code2 size={19} />
                  ) : (
                    <Target size={19} />
                  )}
                </span>

                <div>
                  <span className="eyebrow">
                    {question.concept}
                  </span>

                  <h3>
                    {question.prompt}
                  </h3>
                </div>
              </div>

              <fieldset
                disabled={locked}
                className="answer-fields"
              >
                <legend>Your attempt</legend>

                {question.options ? (
                  <div className="answer-options">
                    {question.options.map(
                      (
                        option,
                        index,
                      ) => (
                        <label
                          key={option}
                          className={
                            answer === option
                              ? "chosen"
                              : ""
                          }
                        >
                          <input
                            type="radio"
                            name="practice-answer"
                            value={option}
                            checked={
                              answer ===
                              option
                            }
                            onChange={() => {
                              setAnswer(
                                option,
                              );
                              setFeedback(
                                null,
                              );
                            }}
                          />

                          <span className="option-letter">
                            {String.fromCharCode(
                              65 + index,
                            )}
                          </span>

                          <span>
                            {option}
                          </span>
                        </label>
                      ),
                    )}
                  </div>
                ) : (
                  <>
                    <label
                      className="sr-only"
                      htmlFor="practice-answer"
                    >
                      {mode === "code"
                        ? "Your code"
                        : "Your numerical answer"}
                    </label>

                    <textarea
                      id="practice-answer"
                      className={
                        mode === "code"
                          ? "code-input"
                          : ""
                      }
                      rows={
                        mode === "code"
                          ? 11
                          : 3
                      }
                      maxLength={12000}
                      spellCheck={
                        mode !== "code"
                      }
                      value={answer}
                      onChange={(event) => {
                        setAnswer(
                          event.target.value,
                        );
                        setFeedback(null);
                      }}
                      placeholder={
                        mode === "code"
                          ? "Write your solution here…"
                          : "Enter your answer…"
                      }
                    />
                  </>
                )}
              </fieldset>

              {question.hint && (
                <details className="hint">
                  <summary>
                    <Lightbulb size={16} />
                    Need a small hint?
                  </summary>

                  <p>
                    {question.hint}
                  </p>
                </details>
              )}

              {mode === "code" && (
                <p className="field-help">
                  Code review checks a few common
                  mistake patterns. Your code is not
                  executed, and a review is not proof
                  of correctness.
                </p>
              )}

              <button
                className="primary"
                disabled={
                  locked ||
                  !answer.trim()
                }
                onClick={() =>
                  void submit()
                }
              >
                {submitting ? (
                  <BusyLabel
                    text="Checking your attempt…"
                  />
                ) : (
                  <>
                    {mode === "code"
                      ? "Review my attempt"
                      : "Check my answer"}

                    <ArrowRight
                      size={17}
                    />
                  </>
                )}
              </button>

              {feedback && (
                <section
                  className={`feedback ${
                    feedback.correct === true
                      ? "positive"
                      : ""
                  }`}
                  aria-live="polite"
                >
                  <div className="inline">
                    <CheckCircle2
                      size={20}
                    />

                    <h3>
                      {feedback.correct ===
                      true
                        ? "That’s the connection."
                        : feedback.verdict ===
                            "reviewed"
                          ? "Review complete"
                          : "Let’s work through this."}
                    </h3>
                  </div>

                  <p>
                    {feedback.explanation}
                  </p>

                  <div className="button-row">
                    <button
                      className="secondary"
                      disabled={locked}
                      onClick={() => {
                        if (
                          !questions.some(
                            (item) =>
                              item.id ===
                              feedback
                                .follow_up
                                .id,
                          )
                        ) {
                          setQuestions(
                            (
                              previous,
                            ) => [
                              ...previous,
                              feedback.follow_up,
                            ],
                          );
                        }

                        changeQuestion(
                          feedback.follow_up
                            .id,
                        );
                      }}
                    >
                      Try the follow-up

                      <ArrowRight
                        size={16}
                      />
                    </button>

                    <button
                      className="text-button"
                      disabled={locked}
                      onClick={() =>
                        askTutor(
                          `Help me understand my practice feedback.\nQuestion: ${question.prompt}\nMy attempt: ${answer}\nFeedback: ${feedback.explanation}\nGuide me with a hint before giving the full solution.`,
                        )
                      }
                    >
                      Discuss with my tutor
                    </button>
                  </div>
                </section>
              )}
            </>
          )}
        </>
      )}

      <ErrorBox text={error} />

      {!questions.length &&
        !loading && (
          <button
            className="secondary"
            onClick={() =>
              setReload(
                (number) => number + 1,
              )
            }
          >
            Reload questions
          </button>
        )}

      {notice && (
        <p
          className="notice"
          role="status"
        >
          {notice}
        </p>
      )}
    </section>
  );
}

export function ProgressPanel({
  progress,
  memory,
  onPractice,
}: {
  progress: Progress | null;
  memory: Memory | null;
  onPractice: (
    question: Pick<
      Question,
      "id" | "mode"
    >,
  ) => void;
}) {
  const statusLabel = (
    status: string,
  ) =>
    ({
      "on-track":
        "Last answer correct",
      "needs-practice":
        "Needs another attempt",
      reviewed:
        "Code reviewed",
    })[status] || status;

  return (
    <section className="content-card">
      <span className="eyebrow">
        YOUR LEARNING RECORD
      </span>

      <h2>
        See what you’ve worked on.
      </h2>

      <p className="muted">
        A record of your attempts and feedback,
        so you know where to go next.
      </p>

      <div className="record-stats">
        <div>
          <strong>
            {progress?.attempts ?? 0}
          </strong>

          <span>
            Recorded practice attempts
          </span>
        </div>

        <div>
          <strong>
            {memory?.completed_turns ?? 0}
          </strong>

          <span>
            Completed chat turns
          </span>
        </div>

        <div>
          <strong>
            {progress?.concepts.length ?? 0}
          </strong>

          <span>
            Concepts practised
          </span>
        </div>
      </div>

      {!progress?.concepts.length ? (
        <div className="empty-panel">
          <Target size={30} />

          <h3>
            Your first attempt belongs here.
          </h3>

          <p>
            Try a built-in question to start
            your learning record.
          </p>

          <button
            className="secondary"
            onClick={() =>
              onPractice({
                id: "3nf",
                mode: "understand",
              })
            }
          >
            Try a question

            <ArrowRight size={16} />
          </button>
        </div>
      ) : (
        <div className="concept-list">
          {progress.concepts.map(
            (item) => (
              <article
                key={item.concept}
              >
                <div>
                  <h3>
                    {item.concept}
                  </h3>

                  <p>
                    {item.attempts}{" "}
                    attempt(s) ·{" "}
                    {statusLabel(
                      item.latest_status,
                    )}
                  </p>
                </div>

                <button
                  className="secondary"
                  onClick={() =>
                    onPractice(
                      item.follow_up,
                    )
                  }
                >
                  Continue practice

                  <ArrowRight
                    size={16}
                  />
                </button>
              </article>
            ),
          )}
        </div>
      )}

      <p className="field-help">
        The attempt count covers the latest
        200 practice attempts. Chat turns
        include any earlier mock tests. This
        is not a calibrated mastery score.
      </p>

      {!!memory?.learning_state
        .weak_concepts?.length && (
        <div className="focus-block">
          <h3>
            Worth another look
          </h3>

          <div className="tags">
            {memory.learning_state.weak_concepts.map(
              (item) => (
                <span
                  className="tag amber"
                  key={item}
                >
                  {item}
                </span>
              ),
            )}
          </div>
        </div>
      )}

      {memory?.recap && (
        <details className="recap">
          <summary>
            Saved conversation recap
          </summary>

          <p className="field-help">
            An extractive recap of older
            turns. Recent turns are kept
            separately in the conversation
            context.
          </p>

          <p className="plain-message">
            {memory.recap}
          </p>
        </details>
      )}
    </section>
  );
}