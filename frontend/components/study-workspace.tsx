"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import {
  ArrowRight,
  ArrowUp,
  BookOpen,
  Check,
  ChevronRight,
  Code2,
  FileText,
  GraduationCap,
  Layers3,
  LoaderCircle,
  Menu,
  MessageSquare,
  Plus,
  RefreshCw,
  Target,
  Upload,
  X,
} from "lucide-react";
import { api, errorText, patchJson, postFile, postJson } from "@/lib/api";
import type {
  ChatRequest,
  ChatResult,
  DocumentInfo,
  Memory,
  Message,
  Mode,
  Progress,
  Provider,
  Providers,
  Session,
  Video,
} from "@/lib/types";
import { Markdown } from "./markdown";
import { PracticePanel, ProgressPanel } from "./practice-panel";
import { PracticeTestPanel } from "./practice-test-panel";
import { CodePracticePanel } from "./code-practice-panel";
import { DataLab, VideoPanel } from "./resources";
import { BusyLabel, ErrorBox } from "./ui";

type View =
  | "tutor"
  | "practice"
  | "practice-test"
  | "data"
  | "videos"
  | "progress";

type WorkspaceSession = Session & {
  degree?: string;
  subject?: string;
};
const views: { id: View; label: string }[] = [
  { id: "tutor", label: "Tutor" },
  { id: "practice", label: "Try a question" },
  { id: "practice-test", label: "Practice Test" },
  { id: "data", label: "Data lab" },
  { id: "videos", label: "Video clips" },
  { id: "progress", label: "Learning record" },
];
const modes: { id: Mode; label: string; icon: typeof BookOpen }[] = [
  { id: "understand", label: "Understand", icon: BookOpen },
  { id: "practise", label: "Practise", icon: Target },
  { id: "code", label: "Code", icon: Code2 },
];
export const providerLabel = (name: string | null) =>
  ({
    auto: "Auto",
    gemini: "Gemini",
    openai: "OpenAI",
    anthropic: "Claude",
    mock: "Mock demo",
    none: "New session",
  })[name || "none"] || name;

function dateLabel(raw: string) {
  const date = new Date(/[Z+-]\d*:?\d*$/.test(raw) ? raw : `${raw}Z`);
  return Number.isNaN(date.getTime())
    ? "Saved session"
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function StudyWorkspace() {
  const [sessions, setSessions] = useState<WorkspaceSession[]>([]);
  const [providers, setProviders] = useState<Providers | null>(null);
  const [activeId, setActiveId] = useState("");
  const [view, setView] = useState<View>("tutor");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const connect = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const [saved, settings] = await Promise.all([
        api<WorkspaceSession[]>("/sessions", { signal }),
        api<Providers>("/providers", { signal }),
        api("/ready", { signal }),
      ]);
      if (signal?.aborted) return;
      setSessions(saved);
      setProviders(settings);
      setConnected(true);
      setActiveId((current) => {
        let remembered = current;
        try {
          remembered ||= localStorage.getItem("conceptbridge:last-session") || "";
        } catch {
          /* Optional device preference. */
        }
        return saved.some((s) => s.session_id === remembered)
          ? remembered
          : saved[0]?.session_id || "";
      });
    } catch (err) {
      if (!signal?.aborted) {
        setError(errorText(err));
        setConnected(false);
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void connect(controller.signal);
    return () => controller.abort();
  }, [connect]);
  useEffect(() => {
    if (activeId) {
      try {
        localStorage.setItem("conceptbridge:last-session", activeId);
      } catch {
        /* The API remains authoritative. */
      }
    }
  }, [activeId]);
  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await api<WorkspaceSession[]>("/sessions"));
    } catch {
      /* Already saved work remains visible; Reconnect refreshes the list. */
    }
  }, []);
  const current = sessions.find((s) => s.session_id === activeId);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace">
        Skip to learning workspace
      </a>
      <aside className={`sidebar ${mobileOpen ? "is-open" : ""}`} aria-label="Sessions">
        <a href="#workspace" className="brand">
          <span className="brand-icon">
            <Layers3 size={23} />
          </span>
          <span>
            ConceptBridge<small>Make the connection.</small>
          </span>
        </a>
        <div className="sidebar-intro">
          <span className="eyebrow">YOUR STUDY SPACE</span>
          <p>
            A little clearer.
            <br />A little further.
          </p>
        </div>
        <button
          className="new-session"
          onClick={() => setCreateOpen(true)}
          disabled={!connected || busy || loading}
        >
          <Plus size={18} />
          New learning session
        </button>
        <div className="session-list-heading">
          <span>RECENT SESSIONS</span>
          <span>{sessions.length}</span>
        </div>
        <nav className="session-list" aria-label="Choose learning session">
          {sessions.map((session) => (
            <button
              key={session.session_id}
              className={`session-item ${activeId === session.session_id ? "active" : ""}`}
              aria-current={activeId === session.session_id ? "page" : undefined}
              disabled={busy}
              onClick={() => {
                setActiveId(session.session_id);
                setMobileOpen(false);
                setView("tutor");
              }}
            >
              <MessageSquare size={17} />
              <span>
                <strong>{session.topic}</strong>
                <small>
                  {dateLabel(session.updated_at)} · {providerLabel(session.provider)}
                </small>
              </span>
            </button>
          ))}
          {!sessions.length && (
            <p className="sidebar-empty">
              {loading ? "Loading your sessions…" : "Create a session to start learning."}
            </p>
          )}
        </nav>
        <div className="sidebar-bottom">
          <GraduationCap size={20} />
          <div>
            <strong>Your learning, connected</strong>
            <small>MCA · BCA · MBA · BBA</small>
          </div>
        </div>
        <p className="local-label">Local development edition</p>
      </aside>
      <div className="app-main">
        <header className="topbar">
          <div className="inline">
            <button
              className="icon-button mobile-menu"
              aria-label="Toggle sessions"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              <Menu size={21} />
            </button>
            <span className="topbar-label">Learning workspace</span>
          </div>
          <div className="inline">
            <span className={`connection ${connected ? "online" : ""}`}>
              <i />
              {loading ? "Connecting" : connected ? "Backend connected" : "Backend offline"}
            </span>
            <button
              className="icon-button"
              title="Reconnect and refresh sessions"
              aria-label="Reconnect and refresh sessions"
              disabled={busy || loading}
              onClick={() => void connect()}
            >
              <RefreshCw size={17} className={loading ? "spin" : ""} />
            </button>
          </div>
        </header>
        <main id="workspace" className="workspace" tabIndex={-1}>
          <ErrorBox text={error} />
          {current && providers ? (
            <SessionWorkspace
              key={current.session_id}
              session={current}
              providers={providers}
              view={view}
              setView={setView}
              setParentBusy={setBusy}
              onSaved={refreshSessions}
              connected={connected}
            />
          ) : (
            <section className="welcome-state">
              <span className="welcome-icon">
                <BookOpen size={32} />
              </span>
              <span className="eyebrow">ONE CONCEPT AT A TIME</span>
              <h1>
                Your next breakthrough
                <br />
                starts with a question.
              </h1>
              <p>
                Create a learning session, add your class notes, and work through a concept with
                your tutor.
              </p>
              <button
                className="primary"
                disabled={loading || !connected}
                onClick={() => setCreateOpen(true)}
              >
                {loading ? (
                  <BusyLabel text="Connecting…" />
                ) : (
                  <>
                    Start a learning session
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
              {!connected && !loading && (
                <button className="text-button" onClick={() => void connect()}>
                  Reconnect to the backend
                </button>
              )}
            </section>
          )}
        </main>
      </div>
      {createOpen && (
        <NewSession
          onClose={() => setCreateOpen(false)}
          onCreated={(session) => {
            setSessions((previous) => [session, ...previous]);
            setActiveId(session.session_id);
            setView("tutor");
            setCreateOpen(false);
            setMobileOpen(false);
          }}
        />
      )}
    </div>
  );
}

function NewSession({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (session: WorkspaceSession) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Curriculum state
  const [degrees, setDegrees] = useState<string[]>([]);
  const [subjects, setSubjects] = useState<string[]>([]);
  const [topics, setTopics] = useState<string[]>([]);

  const [degree, setDegree] = useState("MCA");
  const [subject, setSubject] = useState("");
  const [topic, setTopic] = useState("");

  const [customDegree, setCustomDegree] = useState("");
  const [customSubject, setCustomSubject] = useState("");
  const [customTopic, setCustomTopic] = useState("");

  const [loadingDegrees, setLoadingDegrees] = useState(true);
  const [loadingSubjects, setLoadingSubjects] = useState(false);
  const [loadingTopics, setLoadingTopics] = useState(false);

  const [curriculumError, setCurriculumError] = useState("");

  useEffect(() => {
    dialog.current?.showModal();
  }, []);

  // ============================================================
  // LOAD DEGREES
  // ============================================================

  useEffect(() => {
    const controller = new AbortController();

    setLoadingDegrees(true);
    setCurriculumError("");

    api<{ degrees: string[] }>(
      "/curriculum/degrees",
      { signal: controller.signal },
    )
      .then((result) => {
        if (controller.signal.aborted) return;

        setDegrees(result.degrees);

        if (result.degrees.includes("MCA")) {
          setDegree("MCA");
        } else if (result.degrees.length > 0) {
          setDegree(result.degrees[0]);
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setCurriculumError(errorText(err));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingDegrees(false);
        }
      });

    return () => controller.abort();
  }, []);

  // ============================================================
  // LOAD SUBJECTS WHEN DEGREE CHANGES
  // ============================================================

  useEffect(() => {
    if (!degree || degree === "Other") {
      setSubjects(["Other"]);
      setSubject("Other");
      setTopics(["Other"]);
      setTopic("Other");
      return;
    }

    const controller = new AbortController();

    setLoadingSubjects(true);
    setCurriculumError("");

    setSubject("");
    setTopic("");
    setCustomSubject("");
    setCustomTopic("");

    api<{ degree: string; subjects: string[] }>(
      `/curriculum/${encodeURIComponent(degree)}/subjects`,
      { signal: controller.signal },
    )
      .then((result) => {
        if (controller.signal.aborted) return;

        setSubjects(result.subjects);

        const firstSubject =
          result.subjects.find(
            (item) => item !== "Other",
          ) || "Other";

        setSubject(firstSubject);
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setSubjects(["Other"]);
          setSubject("Other");
          setCurriculumError(errorText(err));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingSubjects(false);
        }
      });

    return () => controller.abort();
  }, [degree]);

  // ============================================================
  // LOAD TOPICS WHEN SUBJECT CHANGES
  // ============================================================

  useEffect(() => {
    if (!degree || degree === "Other") {
      setTopics(["Other"]);
      setTopic("Other");
      return;
    }

    if (!subject || subject === "Other") {
      setTopics(["Other"]);
      setTopic("Other");
      return;
    }

    const controller = new AbortController();

    setLoadingTopics(true);
    setCurriculumError("");

    setTopic("");
    setCustomTopic("");

    api<{
      degree: string;
      subject: string;
      topics: string[];
    }>(
      `/curriculum/${encodeURIComponent(
        degree,
      )}/${encodeURIComponent(subject)}/topics`,
      { signal: controller.signal },
    )
      .then((result) => {
        if (controller.signal.aborted) return;

        setTopics(result.topics);

        const firstTopic =
          result.topics.find(
            (item) => item !== "Other",
          ) || "Other";

        setTopic(firstTopic);
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setTopics(["Other"]);
          setTopic("Other");
          setCurriculumError(errorText(err));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingTopics(false);
        }
      });

    return () => controller.abort();
  }, [degree, subject]);

  // ============================================================
  // CREATE SESSION
  // ============================================================

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (saving) return;

    const finalDegree =
      degree === "Other"
        ? customDegree.trim()
        : degree.trim();

    const finalSubject =
      subject === "Other"
        ? customSubject.trim()
        : subject.trim();

    const finalTopic =
      topic === "Other"
        ? customTopic.trim()
        : topic.trim();

    if (!finalDegree) {
      setError("Enter the degree name.");
      return;
    }

    if (!finalSubject) {
      setError("Enter the subject name.");
      return;
    }

    if (!finalTopic) {
      setError("Enter the topic name.");
      return;
    }

    setSaving(true);
    setError("");
    setCurriculumError("");

    try {
      const result = await postJson<{ session_id: string }>(
        "/demo/session",
        {
          degree: finalDegree,
          subject: finalSubject,
          topic: finalTopic,
        },
      );

      onCreated({
        session_id: result.session_id,
        degree: finalDegree,
        subject: finalSubject,
        topic: finalTopic,
        provider: "none",
        updated_at: new Date().toISOString(),
      });
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <dialog
      ref={dialog}
      className="dialog"
      aria-labelledby="new-title"
      onCancel={(event) => {
        if (saving) {
          event.preventDefault();
        } else {
          onClose();
        }
      }}
    >
      <form onSubmit={create}>
        <div className="section-heading">
          <span className="eyebrow">
            A FRESH START
          </span>

          <button
            type="button"
            className="icon-button"
            aria-label="Close new session"
            onClick={onClose}
            disabled={saving}
          >
            <X size={20} />
          </button>
        </div>

        <h2 id="new-title">
          What are you learning?
        </h2>

        <p className="muted">
          Your notes, questions, and practice stay
          together in this session.
        </p>

        <fieldset
          disabled={saving}
          className="form-stack"
        >
          {/* ==================================================
              DEGREE
              ================================================== */}

          <label>
            Degree

            <select
              value={degree}
              onChange={(event) => {
                setDegree(event.target.value);
                setError("");
              }}
              disabled={loadingDegrees}
            >
              {loadingDegrees ? (
                <option value="">
                  Loading degrees...
                </option>
              ) : (
                degrees.map((item) => (
                  <option
                    key={item}
                    value={item}
                  >
                    {item}
                  </option>
                ))
              )}
            </select>
          </label>

          {/* ==================================================
              CUSTOM DEGREE
              ================================================== */}

          {degree === "Other" && (
            <label>
              Enter your degree

              <input
                value={customDegree}
                onChange={(event) =>
                  setCustomDegree(event.target.value)
                }
                placeholder="e.g. B.Tech, M.Tech, B.Sc"
                maxLength={150}
                required
                autoFocus
              />

              <small className="muted">
                Enter your degree if it is not listed.
              </small>
            </label>
          )}

          {/* ==================================================
              SUBJECT
              ================================================== */}

          <label>
            Subject

            {degree === "Other" ? (
              <input
                value={customSubject}
                onChange={(event) =>
                  setCustomSubject(event.target.value)
                }
                placeholder="e.g. Computer Networks"
                maxLength={150}
                required
              />
            ) : (
              <select
                value={subject}
                onChange={(event) => {
                  setSubject(event.target.value);
                  setError("");
                }}
                disabled={
                  loadingSubjects ||
                  subjects.length === 0
                }
              >
                {loadingSubjects ? (
                  <option value="">
                    Loading subjects...
                  </option>
                ) : (
                  subjects.map((item) => (
                    <option
                      key={item}
                      value={item}
                    >
                      {item}
                    </option>
                  ))
                )}
              </select>
            )}
          </label>

          {/* ==================================================
              CUSTOM SUBJECT
              ================================================== */}

          {degree !== "Other" &&
            subject === "Other" && (
              <label>
                Enter your subject

                <input
                  value={customSubject}
                  onChange={(event) =>
                    setCustomSubject(
                      event.target.value,
                    )
                  }
                  placeholder="e.g. Advanced Database Systems"
                  maxLength={150}
                  required
                />

                <small className="muted">
                  Enter your subject if it is not listed.
                </small>
              </label>
            )}

          {/* ==================================================
              TOPIC
              ================================================== */}

          <label>
            Topic

            {degree === "Other" ||
            subject === "Other" ? (
              <input
                value={customTopic}
                onChange={(event) =>
                  setCustomTopic(event.target.value)
                }
                placeholder="e.g. Third Normal Form"
                maxLength={255}
                required
              />
            ) : (
              <select
                value={topic}
                onChange={(event) => {
                  setTopic(event.target.value);
                  setError("");
                }}
                disabled={
                  loadingTopics ||
                  topics.length === 0
                }
              >
                {loadingTopics ? (
                  <option value="">
                    Loading topics...
                  </option>
                ) : (
                  topics.map((item) => (
                    <option
                      key={item}
                      value={item}
                    >
                      {item}
                    </option>
                  ))
                )}
              </select>
            )}
          </label>

          {/* ==================================================
              CUSTOM TOPIC
              ================================================== */}

          {degree !== "Other" &&
            subject !== "Other" &&
            topic === "Other" && (
              <label>
                Enter your topic

                <input
                  value={customTopic}
                  onChange={(event) =>
                    setCustomTopic(
                      event.target.value,
                    )
                  }
                  placeholder="e.g. Advanced Normalization"
                  maxLength={255}
                  required
                />

                <small className="muted">
                  Enter your topic if it is not listed.
                </small>
              </label>
            )}

          {/* ==================================================
              ERRORS
              ================================================== */}

          <ErrorBox text={curriculumError} />
          <ErrorBox text={error} />

          {/* ==================================================
              CREATE
              ================================================== */}

          <button
            className="primary"
            type="submit"
            disabled={
              saving ||
              loadingDegrees ||
              loadingSubjects ||
              loadingTopics
            }
          >
            {saving ? (
              <BusyLabel text="Creating…" />
            ) : (
              <>
                Create session
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </fieldset>
      </form>
    </dialog>
  );
}

function SessionWorkspace({
  session,
  providers,
  view,
  setView,
  setParentBusy,
  onSaved,
  connected,
}: {
  session: WorkspaceSession;
  providers: Providers;
  view: View;
  setView: (view: View) => void;
  setParentBusy: (busy: boolean) => void;
  onSaved: () => Promise<void>;
  connected: boolean;
}) {
  const [mode, setMode] = useState<Mode>("understand");
  const [practiceQuestion, setPracticeQuestion] = useState("");
  const [provider, setProvider] = useState<Provider>("auto");
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [memory, setMemory] = useState<Memory | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [draft, setDraft] = useState("");
  const [retry, setRetry] = useState<ChatRequest | null>(null);
  const [lastResult, setLastResult] = useState<ChatResult | null>(null);
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [busy, setBusy] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [chatError, setChatError] = useState("");
  const [notice, setNotice] = useState("");
  const [reload, setReload] = useState(0);
  const chatEnd = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const path = `/sessions/${session.session_id}`;
  const locked = !!busy || loading || !connected || !!loadError;
  const begin = (name: string) => {
    setBusy(name);
    setParentBusy(true);
  };
  const finish = () => {
    setBusy("");
    setParentBusy(false);
  };

  useEffect(() => {
    const controller = new AbortController();
    const options = { signal: controller.signal };
    setLoading(true);
    setLoadError("");
    Promise.all([
      api<Message[]>(`${path}/messages?limit=200`, options),
      api<DocumentInfo[]>(`${path}/documents`, options),
      api<Memory>(`${path}/memory`, options),
      api<Progress>(`${path}/progress`, options),
      api<Video[]>(`${path}/videos`, options),
    ])
      .then(([history, notes, state, record, clips]) => {
        if (!controller.signal.aborted) {
          setMessages(history);
          setDocuments(notes);
          setMemory(state);
          setProgress(record);
          setVideos(clips);
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) setLoadError(errorText(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [path, reload]);
  useEffect(() => {
    if (view === "tutor")
      chatEnd.current?.scrollIntoView({ behavior: "instant", block: "nearest" });
  }, [messages.length, busy, view]);

  async function refreshLearning() {
    const [state, record] = await Promise.all([
      api<Memory>(`${path}/memory`),
      api<Progress>(`${path}/progress`),
    ]);
    setMemory(state);
    setProgress(record);
  }

  async function send(savedRequest?: ChatRequest) {
    if (locked || (!savedRequest && !draft.trim())) return;
    const request: ChatRequest = savedRequest || {
      session_id: session.session_id,
      request_id: crypto.randomUUID(),
      message: draft.trim(),
      provider,
      mode,
      allow_fallback: false,
    };
    begin("chat");
    setChatError("");
    setNotice("");
    setPendingQuestion(request.message);
    let committed = false;
    try {
      const result = await postJson<ChatResult>("/chat", request);
      committed = true;
      setLastResult(result);
      setDraft("");
      setRetry(null);
      setMessages((previous) => [
        ...previous,
        { id: `${result.request_id}:user`, role: "user", content: request.message, provider: null },
        {
          id: `${result.request_id}:assistant`,
          role: "assistant",
          content: result.response,
          provider: result.provider_used,
        },
      ]);
      await refreshLearning();
      await onSaved();
    } catch (err) {
      if (committed)
        setNotice(
          "Your reply was saved. The learning record could not refresh; use Reload session to update it.",
        );
      else {
        setChatError(errorText(err));
        setRetry(request);
      }
    } finally {
      setPendingQuestion("");
      finish();
      composer.current?.focus();
    }
  }

  const ask = (text: string) => {
    setDraft(text);
    setRetry(null);
    setChatError("");
    setView("tutor");
    setTimeout(() => composer.current?.focus(), 0);
  };

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">YOUR CURRENT FOCUS</div>
          <h1>{session.topic}</h1>
          <p>Build understanding. Make an attempt. Keep moving.</p>
        </div>
        <div className="topic-mark">
          <BookOpen size={28} />
        </div>
      </div>
      <div className="mode-bar">
        <div className="mode-switch" aria-label="Learning mode">
          {modes.map((item) => (
            <button
              key={item.id}
              className={mode === item.id ? "selected" : ""}
              aria-pressed={mode === item.id}
              disabled={!!busy}
              onClick={() => {
                setMode(item.id);
                setPracticeQuestion("");
              }}
            >
              <item.icon size={17} />
              {item.label}
            </button>
          ))}
        </div>
        <span className="mode-description">
          {mode === "understand"
            ? "Connect the ideas behind the answer."
            : mode === "practise"
              ? "Turn an explanation into something you can do."
              : "Think through the logic, one step at a time."}
        </span>
      </div>
      <div className="workspace-tabs" aria-label="Learning activities">
        {views.map((item) => (
          <button
            key={item.id}
            aria-pressed={view === item.id}
            className={view === item.id ? "selected" : ""}
            disabled={!!busy}
            onClick={() => setView(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <ErrorBox text={loadError} />
      {loadError && (
        <button className="secondary" onClick={() => setReload((n) => n + 1)}>
          Reload session
        </button>
      )}
      {notice && (
        <div className="notice" role="status">
          {notice}
          <button
            className="text-button"
            disabled={!!busy}
            onClick={() => {
              setNotice("");
              setReload((n) => n + 1);
            }}
          >
            Reload session
          </button>
        </div>
      )}
      {loading ? (
        <div className="loading-panel">
          <BusyLabel text="Opening your saved learning session…" />
        </div>
      ) : (
        <div className={`learning-layout ${view !== "tutor" && view !== "practice" || mode === "code" || mode === "practise" ? "wide" : ""}`}>
          <div className="activity-panel">
            {view === "tutor" && mode === "code" && (
              <CodePracticePanel
                degree={session.degree || ""}
                subject={session.subject || ""}
                topic={session.topic}
                locked={locked}
              />
            )}
            {view === "tutor" && mode !== "code" && mode !== "practise" && (
              <section className="chat-panel" aria-label="Chat with your tutor">
                <div className="panel-heading">
                  <div className="inline">
                    <span className="small-icon">
                      <Layers3 size={18} />
                    </span>
                    <div>
                      <h2>Your learning partner</h2>
                      <p>Your conversation and notes travel together.</p>
                    </div>
                  </div>
                  <label className="provider-select">
                    <span>AI provider</span>
                    <select
                      value={provider}
                      disabled={locked || !!retry}
                      onChange={(event) => setProvider(event.target.value as Provider)}
                    >
                      <option value="auto">Auto</option>
                      {providers.providers.map((item) => (
                        <option key={item.id} value={item.id} disabled={!item.configured}>
                          {providerLabel(item.id)}
                          {!item.configured ? " · no key" : ""}
                        </option>
                      ))}
                      {providers.mock_enabled && <option value="mock">Mock demo</option>}
                    </select>
                  </label>
                </div>
                {providers.default_provider === "mock" && (
                  <div className="notice">
                    Auto currently uses mock replies. Select a configured provider for an AI answer.
                  </div>
                )}
                <div className="message-list" aria-label="Conversation" aria-busy={busy === "chat"}>
                  {!messages.length && (
                    <div className="chat-empty">
                      <BookOpen size={30} />
                      <h3>Let’s make this click.</h3>
                      <p>Ask about {session.topic}, or start with one of these.</p>
                      <div className="suggestions">
                        {[
                          "Explain this topic using a simple worked example.",
                          "Using my uploaded notes, explain this topic and cite the relevant note chunks.",
                          "Ask me one question to check my understanding of this topic.",
                        ].map((text) => (
                          <button key={text} disabled={locked} onClick={() => ask(text)}>
                            {text}
                            <ArrowRight size={16} />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {messages.map((message, index) => (
                    <article
                      key={message.id}
                      className={`message ${message.role === "user" ? "user" : "assistant"}`}
                    >
                      <div className="message-meta">
                        <span className="avatar">
                          {message.role === "user" ? "Y" : <Layers3 size={15} />}
                        </span>
                        <strong>{message.role === "user" ? "You" : "ConceptBridge"}</strong>
                        {message.provider && (
                          <span
                            className={`tag ${message.provider === "mock" ? "amber" : "green"}`}
                          >
                            {providerLabel(message.provider)}
                          </span>
                        )}
                      </div>
                      <div className="message-content">
                        {message.role === "user" ? (
                          <p className="plain-message">{message.content}</p>
                        ) : (
                          <Markdown text={message.content} />
                        )}
                      </div>
                      {index === messages.length - 1 &&
                        lastResult &&
                        message.role === "assistant" && (
                          <details className="reply-details">
                            <summary>
                              Reply details
                              {lastResult.context.source_chunks.length > 0
                                ? ` · ${lastResult.context.source_chunks.length} note chunk(s) supplied`
                                : ""}
                            </summary>
                            <p>
                              {lastResult.is_mock
                                ? "Mock response"
                                : `Answered by ${providerLabel(lastResult.provider_used)}`}
                              {lastResult.provider_changed
                                ? ` · changed from ${providerLabel(lastResult.previous_provider)}`
                                : ""}
                              . {lastResult.context.recent_messages} recent messages included.{" "}
                              {lastResult.fallback_used
                                ? "A fallback provider was used."
                                : "No fallback was used."}
                            </p>
                            {lastResult.context.source_chunks.length > 0 && (
                              <>
                                <p>Supplied note chunk IDs (keyword retrieval):</p>
                                <ul>
                                  {lastResult.context.source_chunks.map((chunk) => (
                                    <li key={chunk}>
                                      <code>{chunk}</code>
                                    </li>
                                  ))}
                                </ul>
                                <p>
                                  These IDs show the source context supplied to the tutor; they are
                                  not an independent fact check.
                                </p>
                              </>
                            )}
                          </details>
                        )}
                    </article>
                  ))}
                  {pendingQuestion && (
                    <article className="message pending">
                      <div className="message-meta">
                        <span className="avatar">Y</span>
                        <strong>You</strong>
                        <span className="muted">Sending</span>
                      </div>
                      <p className="plain-message">{pendingQuestion}</p>
                      <div className="thinking" role="status">
                        <BusyLabel text="Your tutor is working through it…" />
                      </div>
                    </article>
                  )}
                  <div ref={chatEnd} />
                </div>
                <div className="composer-area">
                  <ErrorBox text={chatError} />
                  {retry && (
                    <div className="retry-row">
                      <span>
                        The reply was not confirmed. Retry sends the same request ID to avoid saving
                        a duplicate turn.
                      </span>
                      <button
                        className="secondary"
                        disabled={locked}
                        onClick={() => void send(retry)}
                      >
                        Retry message
                      </button>
                      <button
                        className="text-button"
                        disabled={locked}
                        onClick={() => {
                          setRetry(null);
                          setChatError("");
                        }}
                      >
                        Edit question
                      </button>
                    </div>
                  )}
                  <form
                    className="composer"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void send();
                    }}
                  >
                    <label className="sr-only" htmlFor="chat-draft">
                      Your question
                    </label>
                    <textarea
                      id="chat-draft"
                      ref={composer}
                      rows={3}
                      maxLength={12000}
                      value={draft}
                      disabled={locked || !!retry}
                      onChange={(event) => setDraft(event.target.value)}
                      placeholder={
                        mode === "code"
                          ? "Paste your code and describe where you’re stuck…"
                          : "Ask a question, share an attempt, or explore an idea…"
                      }
                      onKeyDown={(event) => {
                        if (
                          event.key === "Enter" &&
                          !event.shiftKey &&
                          !event.nativeEvent.isComposing
                        ) {
                          event.preventDefault();
                          if (!retry) void send();
                        }
                      }}
                    />
                    <div className="composer-footer">
                      <span>
                        <BookOpen size={14} />
                        {documents.length
                          ? `${documents.length} note file(s) attached`
                          : "Add your notes for course context"}
                      </span>
                      <button
                        className="send-button"
                        type="submit"
                        disabled={locked || !!retry || !draft.trim()}
                        aria-label="Send question"
                      >
                        {busy === "chat" ? (
                          <LoaderCircle size={19} className="spin" />
                        ) : (
                          <ArrowUp size={20} />
                        )}
                      </button>
                    </div>
                  </form>
                  <p className="composer-hint">
                    Enter to send · Shift + Enter for a new line. AI answers can contain mistakes.
                  </p>
                </div>
              </section>
            )}
            {view === "tutor" && mode === "practise" && (
              <PracticeTestPanel
                sessionId={session.session_id}
                locked={locked}
                begin={begin}
                finish={finish}
              />
            )}
            {view === "practice" && (
              <PracticePanel
                key={`${mode}:${practiceQuestion}`}
                initialQuestionId={practiceQuestion}
                mode={mode}
                sessionId={session.session_id}
                locked={locked}
                begin={begin}
                finish={finish}
                onSaved={refreshLearning}
                askTutor={ask}
              />
            )}
            {view === "practice-test" && (
              <PracticeTestPanel
                sessionId={session.session_id}
                locked={locked}
                begin={begin}
                finish={finish}
              />
            )}
            {view === "data" && (
              <DataLab
                key={session.session_id}
                sessionId={session.session_id}
                locked={locked}
                begin={begin}
                finish={finish}
              />
            )}
            {view === "videos" && (
              <VideoPanel
                sessionId={session.session_id}
                topic={session.topic}
                videos={videos}
                setVideos={setVideos}
                locked={locked}
                begin={begin}
                finish={finish}
              />
            )}
            {view === "progress" && (
              <ProgressPanel
                progress={progress}
                memory={memory}
                onPractice={(question) => {
                  setMode(question.mode);
                  setPracticeQuestion(question.id);
                  setView("practice");
                }}
              />
            )}
          </div>
          {(view === "tutor" || view === "practice") && mode !== "code" && mode !== "practise" && (
            <aside className="context-rail" aria-label="Session notes and learning goal">
              <NotesPanel
                sessionId={session.session_id}
                documents={documents}
                setDocuments={setDocuments}
                locked={locked}
                begin={begin}
                finish={finish}
              />
              <GoalPanel
                memory={memory}
                sessionId={session.session_id}
                locked={locked}
                begin={begin}
                finish={finish}
                onSaved={setMemory}
              />
              <div className="rail-prompt">
                <Target size={22} />
                <h3>Make the next move.</h3>
                <p>
                  Try explaining the idea in your own words. A small attempt gives your tutor
                  something to build on.
                </p>
                <button
                  className="text-button"
                  disabled={locked}
                  onClick={() => setView("practice")}
                >
                  Try a question
                  <ChevronRight size={15} />
                </button>
              </div>
            </aside>
          )}
        </div>
      )}
    </>
  );
}

function NotesPanel({
  sessionId,
  documents,
  setDocuments,
  locked,
  begin,
  finish,
}: {
  sessionId: string;
  documents: DocumentInfo[];
  setDocuments: (documents: DocumentInfo[]) => void;
  locked: boolean;
  begin: (name: string) => void;
  finish: () => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function upload() {
    if (!file || locked) return;
    if (file.size === 0 || file.size > 5_000_000) {
      setError("Choose a non-empty file up to 5 MB.");
      return;
    }
    if (!/\.(pdf|txt|md)$/i.test(file.name)) {
      setError("Choose a PDF, TXT, or Markdown file.");
      return;
    }
    begin("upload");
    setUploading(true);
    setError("");
    setNotice("");
    try {
      const form = new FormData();
      form.append("session_id", sessionId);
      form.append("file", file);
      const result = await postFile<{ document_id: string; filename: string; chunks: number }>(
        "/documents",
        form,
      );
      setDocuments([
        ...documents,
        {
          document_id: result.document_id,
          filename: result.filename,
          retrieval_status: "lexical_ready",
        },
      ]);
      setFile(null);
      if (input.current) input.current.value = "";
      setNotice(`Added ${result.filename}. ${result.chunks} note chunk(s) ready.`);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setUploading(false);
      finish();
    }
  }

  async function deleteDocument(documentId: string, filename: string) {
    if (locked || uploading || deletingId) return;

    const confirmed = window.confirm(
      `Remove "${filename}" from this learning session?`,
    );

    if (!confirmed) return;

    begin("delete-document");
    setDeletingId(documentId);
    setError("");
    setNotice("");

    try {
      await api<{ deleted: boolean; document_id: string }>(
        `/sessions/${sessionId}/documents/${documentId}`,
        { method: "DELETE" },
      );

      setDocuments(
        documents.filter((doc) => doc.document_id !== documentId),
      );
      setNotice(`Removed ${filename}.`);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setDeletingId(null);
      finish();
    }
  }

  return (
    <section className="rail-card">
      <div className="section-heading">
        <h2>
          <FileText size={18} />
          Your notes
        </h2>
        <span className="count">{documents.length}</span>
      </div>
      <p className="muted">Give your tutor the same material you’re studying.</p>
      {documents.length > 0 && (
        <ul className="document-list">
          {documents.map((doc) => {
            const deleting = deletingId === doc.document_id;

            return (
              <li key={doc.document_id}>
                <FileText size={17} />

                <span className="document-info">
                  <strong title={doc.filename}>{doc.filename}</strong>
                  <small>
                    {doc.retrieval_status === "lexical_ready"
                      ? "Ready for questions"
                      : doc.retrieval_status}
                  </small>
                </span>

                <button
                  type="button"
                  className="document-delete"
                  disabled={
                    locked || uploading || deletingId !== null
                  }
                  onClick={() =>
                    void deleteDocument(
                      doc.document_id,
                      doc.filename,
                    )
                  }
                  title={deleting ? "Deleting..." : `Delete ${doc.filename}`}
                  aria-label={
                    deleting
                      ? `Deleting ${doc.filename}`
                      : `Delete ${doc.filename}`
                  }
                >
                  {deleting ? "…" : "×"}
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <label className="file-picker">
        Choose notes
        <input
          ref={input}
          type="file"
          accept=".txt,.md,.pdf"
          disabled={locked}
          onChange={(event) => {
            setFile(event.target.files?.[0] || null);
            setError("");
            setNotice("");
          }}
        />
      </label>
      <p className="field-help">
        PDF, TXT, MD · up to 5 MB
        <br />
        Text PDFs: up to 30 pages. No scanned pages.
      </p>
      <button
        className="secondary full-width"
        disabled={locked || !file}
        onClick={() => void upload()}
      >
        {uploading ? (
          <BusyLabel text="Uploading…" />
        ) : (
          <>
            <Upload size={16} />
            Add to this session
          </>
        )}
      </button>
      <ErrorBox text={error} />
      {notice && (
        <p className="success-text" role="status">
          {notice}
        </p>
      )}
    </section>
  );
}

function GoalPanel({
  memory,
  sessionId,
  locked,
  begin,
  finish,
  onSaved,
}: {
  memory: Memory | null;
  sessionId: string;
  locked: boolean;
  begin: (name: string) => void;
  finish: () => void;
  onSaved: (memory: Memory) => void;
}) {
  const [goal, setGoal] = useState(memory?.learning_state.learning_objective || "");
  const [preference, setPreference] = useState(
    memory?.learning_state.explanation_preference || "Worked examples",
  );
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!memory || locked) return;
    begin("goal");
    setError("");
    setSaved(false);
    try {
      const result = await patchJson<{ learning_state: Memory["learning_state"] }>(
        `/sessions/${sessionId}/memory`,
        { learning_objective: goal.trim(), explanation_preference: preference },
      );
      onSaved({ ...memory, learning_state: result.learning_state });
      setSaved(true);
    } catch (err) {
      setError(errorText(err));
    } finally {
      finish();
    }
  }
  return (
    <section className="rail-card">
      <h2>
        <Target size={18} />
        My learning goal
      </h2>
      <form onSubmit={save} className="form-stack compact">
        <fieldset disabled={locked}>
          <label className="sr-only" htmlFor="learning-goal">
            Learning goal
          </label>
          <textarea
            id="learning-goal"
            rows={3}
            maxLength={600}
            value={goal}
            onChange={(event) => {
              setGoal(event.target.value);
              setSaved(false);
            }}
            placeholder="e.g. Explain 3NF without checking my notes."
          />
          <label>
            Explain with
            <select
              value={preference}
              onChange={(event) => {
                setPreference(event.target.value);
                setSaved(false);
              }}
            >
              {[
                "Worked examples",
                "Small guided hints",
                "Simple analogies",
                "Step-by-step reasoning",
              ].map((value) => (
                <option key={value}>{value}</option>
              ))}
              {preference &&
                ![
                  "Worked examples",
                  "Small guided hints",
                  "Simple analogies",
                  "Step-by-step reasoning",
                ].includes(preference) && <option>{preference}</option>}
            </select>
          </label>
          <button className="text-button" type="submit">
            {saved ? (
              <>
                <Check size={15} />
                Goal saved
              </>
            ) : (
              "Save learning goal"
            )}
          </button>
        </fieldset>
      </form>
      <ErrorBox text={error} />
    </section>
  );
}
