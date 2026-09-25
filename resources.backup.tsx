"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ArrowRight,
  BarChart3,
  ExternalLink,
  FileSpreadsheet,
  Play,
  Plus,
} from "lucide-react";
import { api, errorText, postFile, postJson } from "@/lib/api";
import type { DataChoices, SavedDataAnalysis, Video } from "@/lib/types";
import { BusyLabel, ErrorBox } from "./ui";

type WorkProps = {
  locked: boolean;
  begin: (name: string) => void;
  finish: () => void;
};

const defaultChoices: DataChoices = {
  date_column: "date",
  value_column: "sales",
  category_column: "region",
  grouping: "month",
  aggregation: "sum",
  chart: "line",
};

export function DataLab({
  sessionId,
  locked,
  begin,
  finish,
}: WorkProps & { sessionId: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<SavedDataAnalysis | null>(null);
  const [analyses, setAnalyses] = useState<SavedDataAnalysis[]>([]);
  const [choices, setChoices] = useState<DataChoices>(defaultChoices);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [reload, setReload] = useState(0);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fileInput = useRef<HTMLInputElement>(null);

  const disabled = locked || loading || !!loadError;

  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);
    setLoadError("");

    api<SavedDataAnalysis[]>(
      `/sessions/${sessionId}/data-analyses`,
      { signal: controller.signal },
    )
      .then((saved) => {
        if (controller.signal.aborted) return;

        setAnalyses(saved);
        setResult(saved[0] || null);
        setChoices(saved[0]?.choices || defaultChoices);
        setFile(null);

        if (fileInput.current) {
          fileInput.current.value = "";
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setLoadError(errorText(err));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [sessionId, reload]);

  function chooseSaved(id: string) {
    const saved =
      analyses.find((item) => item.analysis_id === id) || null;

    setResult(saved);
    setChoices(saved?.choices || defaultChoices);
    setFile(null);
    setError("");

    if (fileInput.current) {
      fileInput.current.value = "";
    }
  }

  async function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (disabled || !file) return;

    if (
      !file.name.toLowerCase().endsWith(".csv") ||
      !file.size ||
      file.size > 2_000_000
    ) {
      setError("Choose a non-empty CSV file up to 2 MB.");
      return;
    }

    const data = new FormData(event.currentTarget);

    data.set("file", file);
    data.set("session_id", sessionId);

    begin("data");
    setSubmitting(true);
    setError("");
    setResult(null);

    try {
      const saved = await postFile<SavedDataAnalysis>(
        "/practice/data",
        data,
      );

      setResult(saved);

      setAnalyses((previous) =>
        [saved, ...previous].slice(0, 20),
      );
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSubmitting(false);
      finish();
    }
  }

  return (
    <section className="content-card">
      <div className="section-heading">
        <span className="eyebrow">DATA LAB</span>
        <FileSpreadsheet size={23} />
      </div>

      <h2>Find the story in your sales data.</h2>

      <p className="muted">
        Your task: show the monthly sales trend. Choose how to
        group, aggregate, and present it, then compare with a
        calculated reference. Completed analyses are saved to this
        session.
      </p>

      {loading && (
        <p role="status">
          <BusyLabel text="Loading saved analyses…" />
        </p>
      )}

      <ErrorBox text={loadError} />

      {loadError && (
        <button
          className="secondary"
          disabled={locked}
          onClick={() => setReload((value) => value + 1)}
        >
          Reload saved analyses
        </button>
      )}

      {!!analyses.length && (
        <div className="analysis-history">
          <label>
            Saved analyses

            <select
              disabled={disabled}
              value={result?.analysis_id || ""}
              onChange={(event) =>
                chooseSaved(event.target.value)
              }
            >
              {analyses.map((analysis) => (
                <option
                  key={analysis.analysis_id}
                  value={analysis.analysis_id}
                >
                  {analysis.filename}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      <form
        onSubmit={analyze}
        className="form-stack"
      >
        <fieldset disabled={disabled || submitting}>
          <label>
            CSV file

            <input
              ref={fileInput}
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => {
                setFile(event.target.files?.[0] || null);
                setError("");
              }}
            />
          </label>

          <div className="form-grid">
            <label>
              Date column

              <input
                value={choices.date_column}
                onChange={(event) =>
                  setChoices({
                    ...choices,
                    date_column: event.target.value,
                  })
                }
              />
            </label>

            <label>
              Value column

              <input
                value={choices.value_column}
                onChange={(event) =>
                  setChoices({
                    ...choices,
                    value_column: event.target.value,
                  })
                }
              />
            </label>

            <label>
              Category column

              <input
                value={choices.category_column}
                onChange={(event) =>
                  setChoices({
                    ...choices,
                    category_column: event.target.value,
                  })
                }
              />
            </label>

            <label>
              Grouping

              <select
                value={choices.grouping}
                onChange={(event) =>
                  setChoices({
                    ...choices,
                    grouping: event.target.value,
                  })
                }
              >
                <option value="month">Month</option>
                <option value="region">Region</option>
                <option value="row">Row</option>
              </select>
            </label>

            <label>
              Aggregation

              <select
                value={choices.aggregation}
                onChange={(event) =>
                  setChoices({
                    ...choices,
                    aggregation: event.target.value,
                  })
                }
              >
                <option value="sum">SUM</option>
                <option value="average">Average</option>
                <option value="count">Count</option>
              </select>
            </label>

            <label>
              Chart

              <select
                value={choices.chart}
                onChange={(event) =>
                  setChoices({
                    ...choices,
                    chart: event.target.value,
                  })
                }
              >
                <option value="line">Line</option>
                <option value="bar">Bar</option>
                <option value="pie">Pie</option>
              </select>
            </label>
          </div>

          <button
            className="primary"
            type="submit"
            disabled={!file}
          >
            {submitting ? (
              <BusyLabel text="Analyzing…" />
            ) : (
              <>
                Analyze CSV
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </fieldset>
      </form>

      <ErrorBox text={error} />

      {result && (
        <div className="analysis-result">
          <h3>{result.task}</h3>

          <p>
            <strong>Status:</strong>{" "}
            {result.feedback.verdict}
          </p>

          {result.feedback.issues.length > 0 && (
            <ul>
              {result.feedback.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          )}

          {result.calculated_reference && (
            <div className="reference-card">
              <h4>Calculated reference</h4>

              <pre>
                {JSON.stringify(
                  result.calculated_reference,
                  null,
                  2,
                )}
              </pre>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
export function VideoPanel({
  sessionId,
  topic,
  videos,
  setVideos,
  locked,
  begin,
  finish,
}: WorkProps & {
  sessionId: string;
  topic: string;
  videos: Video[];
  setVideos: (videos: Video[]) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [playingId, setPlayingId] = useState<string | null>(null);

  // YouTube search state
  const [searchQuery, setSearchQuery] = useState(topic);
  const [searchResults, setSearchResults] = useState<
    {
      video_id: string;
      title: string;
      description: string;
      channel_title: string;
      published_at?: string;
      thumbnail?: string;
      youtube_url: string;
    }[]
  >([]);
  const [searching, setSearching] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<{
    video_id: string;
    title: string;
    description: string;
    channel_title: string;
    published_at?: string;
    thumbnail?: string;
    youtube_url: string;
  } | null>(null);

  const [startSeconds, setStartSeconds] = useState(0);
  const [endSeconds, setEndSeconds] = useState(60);
  const [evidence, setEvidence] = useState("");

  async function searchYouTube(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();

    const query = searchQuery.trim();

    if (!query) {
      setError("Enter a topic to search for YouTube videos.");
      return;
    }

    if (query.length < 2) {
      setError("Enter at least 2 characters to search.");
      return;
    }

    begin("video");
    setSearching(true);
    setError("");
    setSelectedVideo(null);

    try {
      const result = await api<{
        query: string;
        results: {
          video_id: string;
          title: string;
          description: string;
          channel_title: string;
          published_at?: string;
          thumbnail?: string;
          youtube_url: string;
        }[];
      }>(
        `/youtube/search?q=${encodeURIComponent(query)}&max_results=8`,
      );

      setSearchResults(result.results);

      if (!result.results.length) {
        setError(
          `No YouTube videos were found for "${query}". Try a broader topic.`,
        );
      }
    } catch (err) {
      setError(errorText(err));
      setSearchResults([]);
    } finally {
      setSearching(false);
      finish();
    }
  }

  function selectVideo(video: {
    video_id: string;
    title: string;
    description: string;
    channel_title: string;
    published_at?: string;
    thumbnail?: string;
    youtube_url: string;
  }) {
    setSelectedVideo(video);
    setStartSeconds(0);
    setEndSeconds(60);
    setEvidence("");
    setError("");
  }

  async function saveSelectedVideo() {
    if (locked || !selectedVideo) return;

    const start = Number(startSeconds);
    const end = Number(endSeconds);
    const relevance = evidence.trim();

    if (end <= start) {
      setError("End time must be after start time.");
      return;
    }

    if (end > 86400 || start < 0) {
      setError("Timestamp must be between 0 and 86400 seconds.");
      return;
    }

    if (relevance.length < 20) {
      setError(
        "Explain the clip's relevance in at least 20 characters.",
      );
      return;
    }

    begin("video");
    setSaving(true);
    setError("");

    try {
      const video = await postJson<Video>("/videos/segments", {
        session_id: sessionId,
        video_id: selectedVideo.video_id,
        title: selectedVideo.title,
        topic: topic,
        start_seconds: start,
        end_seconds: end,
        evidence: relevance,
      });

      setVideos([...videos, video]);

      setSelectedVideo(null);
      setStartSeconds(0);
      setEndSeconds(60);
      setEvidence("");

      setShowForm(false);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
      finish();
    }
  }

  async function addManualVideo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (locked) return;

    const form = new FormData(event.currentTarget);

    const start = Number(form.get("start_seconds"));
    const end = Number(form.get("end_seconds"));
    const relevance = String(form.get("evidence") || "").trim();

    if (end <= start) {
      setError("End time must be after start time.");
      return;
    }

    if (relevance.length < 20) {
      setError(
        "Explain the clip's relevance in at least 20 characters.",
      );
      return;
    }

    begin("video");
    setSaving(true);
    setError("");

    try {
      const video = await postJson<Video>("/videos/segments", {
        session_id: sessionId,
        video_id: String(form.get("video_id") || "").trim(),
        title: String(form.get("title") || "").trim(),
        topic: String(form.get("topic") || "").trim(),
        start_seconds: start,
        end_seconds: end,
        evidence: relevance,
      });

      setVideos([...videos, video]);
      setShowForm(false);
      event.currentTarget.reset();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
      finish();
    }
  }

  const time = (seconds: number) =>
    `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;

  return (
    <section className="content-card">
      <div className="section-heading">
        <span className="eyebrow">WATCH WITH A PURPOSE</span>

        <button
          className="secondary"
          type="button"
          disabled={locked}
          onClick={() => {
            setShowForm(!showForm);
            setError("");
          }}
        >
          <Plus size={16} />
          {showForm ? "Close form" : "Add a clip manually"}
        </button>
      </div>

      <h2>Find useful YouTube videos.</h2>

      <p className="muted">
        Search YouTube for videos related to your current learning
        topic, choose a useful video, and save the exact section you
        want to revisit.
      </p>

      {/* YouTube search */}
      <form
        onSubmit={searchYouTube}
        className="video-search-box form-stack"
      >
        <label>
          Search YouTube
          <input
            type="text"
            value={searchQuery}
            disabled={locked || searching}
            onChange={(event) => {
              setSearchQuery(event.target.value);
              setError("");
            }}
            placeholder="e.g. Binary Search explained"
            maxLength={100}
          />
        </label>

        <button
          className="primary"
          type="submit"
          disabled={locked || searching || !searchQuery.trim()}
        >
          {searching ? (
            <BusyLabel text="Searching YouTube…" />
          ) : (
            <>
              <Play size={16} />
              Search YouTube
            </>
          )}
        </button>
      </form>

      <ErrorBox text={error} />

      {/* Search results */}
      {searchResults.length > 0 && (
        <div className="youtube-results">
          <div className="section-heading">
            <span className="eyebrow">SEARCH RESULTS</span>
            <span className="count">{searchResults.length}</span>
          </div>

          <div className="video-results-list">
            {searchResults.map((video) => (
              <article
                key={video.video_id}
                className={`video-result ${
                  selectedVideo?.video_id === video.video_id
                    ? "selected"
                    : ""
                }`}
              >
                {video.thumbnail && (
                  <img
                    src={video.thumbnail}
                    alt=""
                    className="video-thumbnail"
                  />
                )}

                <div className="video-result-content">
                  <h3>{video.title}</h3>

                  <p className="muted">
                    {video.channel_title}
                  </p>

                  {video.description && (
                    <p className="video-description">
                      {video.description.length > 220
                        ? `${video.description.slice(0, 220)}…`
                        : video.description}
                    </p>
                  )}

                  <div className="inline">
                    <button
                      type="button"
                      className="secondary"
                      disabled={locked}
                      onClick={() => selectVideo(video)}
                    >
                      <Play size={15} />
                      {selectedVideo?.video_id === video.video_id
                        ? "Selected"
                        : "Use this video"}
                    </button>

                    <a
                      className="text-button"
                      href={video.youtube_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open on YouTube
                      <ExternalLink size={14} />
                    </a>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}

      {/* Selected video */}
      {selectedVideo && (
        <div className="selected-video">
          <div className="section-heading">
            <span className="eyebrow">SELECTED VIDEO</span>
          </div>

          <h3>{selectedVideo.title}</h3>

          <p className="muted">
            {selectedVideo.channel_title}
          </p>

          <div className="video-frame">
            <iframe
              src={`https://www.youtube.com/embed/${selectedVideo.video_id}?start=${Math.max(
                0,
                Math.floor(startSeconds),
              )}&playsinline=1&rel=0`}
              title={selectedVideo.title}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
            />
          </div>

          <div className="form-grid">
            <label>
              Start time (seconds)

              <input
                type="number"
                min={0}
                max={86400}
                step={1}
                value={startSeconds}
                disabled={locked || saving}
                onChange={(event) =>
                  setStartSeconds(Number(event.target.value))
                }
              />

              <small>
                Preview starts at {time(startSeconds)}
              </small>
            </label>

            <label>
              End time (seconds)

              <input
                type="number"
                min={1}
                max={86400}
                step={1}
                value={endSeconds}
                disabled={locked || saving}
                onChange={(event) =>
                  setEndSeconds(Number(event.target.value))
                }
              />

              <small>
                Clip ends at {time(endSeconds)}
              </small>
            </label>
          </div>

          <label>
            Why is this clip useful for your topic?

            <textarea
              rows={4}
              minLength={20}
              maxLength={4000}
              value={evidence}
              disabled={locked || saving}
              onChange={(event) =>
                setEvidence(event.target.value)
              }
              placeholder={`Explain how this part of the video helps you understand ${topic}.`}
            />
          </label>

          <div className="inline">
            <button
              type="button"
              className="primary"
              disabled={
                locked ||
                saving ||
                endSeconds <= startSeconds ||
                evidence.trim().length < 20
              }
              onClick={() => void saveSelectedVideo()}
            >
              {saving ? (
                <BusyLabel text="Saving clip…" />
              ) : (
                <>
                  <Plus size={16} />
                  Save this clip
                </>
              )}
            </button>

            <button
              type="button"
              className="secondary"
              disabled={saving}
              onClick={() => {
                setSelectedVideo(null);
                setError("");
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Manual add form */}
      {showForm && (
        <form
          onSubmit={addManualVideo}
          className="video-form form-stack"
        >
          <fieldset disabled={locked || saving}>
            <div className="section-heading">
              <span className="eyebrow">MANUAL CLIP</span>
            </div>

            <div className="form-grid">
              <label>
                Video title

                <input
                  name="title"
                  required
                  maxLength={255}
                  placeholder="Title from YouTube"
                />
              </label>

              <label>
                Topic

                <input
                  name="topic"
                  defaultValue={topic}
                  required
                  maxLength={255}
                />
              </label>

              <label>
                YouTube video ID

                <input
                  name="video_id"
                  required
                  pattern="[A-Za-z0-9_\-]{11}"
                  maxLength={11}
                  placeholder="11-character video ID"
                />

                <small>
                  Copy the 11 characters after v= in the
                  YouTube URL.
                </small>
              </label>

              <div className="form-grid">
                <label>
                  Start (seconds)

                  <input
                    name="start_seconds"
                    type="number"
                    min={0}
                    max={86400}
                    step={1}
                    required
                    defaultValue={0}
                  />
                </label>

                <label>
                  End (seconds)

                  <input
                    name="end_seconds"
                    type="number"
                    min={1}
                    max={86400}
                    step={1}
                    required
                  />
                </label>
              </div>
            </div>

            <label>
              Why is this clip useful?

              <textarea
                name="evidence"
                required
                minLength={20}
                maxLength={4000}
                rows={4}
                placeholder="Explain how this clip connects to the topic."
              />
            </label>

            <button
              className="primary"
              type="submit"
              disabled={saving}
            >
              {saving ? (
                <BusyLabel text="Saving…" />
              ) : (
                <>
                  <Plus size={16} />
                  Save manual clip
                </>
              )}
            </button>
          </fieldset>
        </form>
      )}

      {/* Saved videos */}
      {videos.length > 0 && (
        <div className="saved-videos">
          <div className="section-heading">
            <div>
              <span className="eyebrow">SAVED CLIPS</span>
              <h3>The useful part, bookmarked.</h3>
            </div>

            <span className="count">{videos.length}</span>
          </div>

          <div className="video-list">
            {videos.map((video) => (
              <article
                key={video.id}
                className="saved-video"
              >
                <div className="section-heading">
                  <div>
                    <h3>{video.title}</h3>

                    <p className="muted">
                      {video.topic} · {time(video.start_seconds)}–
                      {time(video.end_seconds)}
                    </p>
                  </div>

                  <button
                    type="button"
                    className="secondary"
                    onClick={() =>
                      setPlayingId(
                        playingId === video.id
                          ? null
                          : video.id,
                      )
                    }
                  >
                    <Play size={15} />
                    {playingId === video.id
                      ? "Hide"
                      : "Watch"}
                  </button>
                </div>

                <p>{video.evidence}</p>

                {playingId === video.id && (
                  <div className="video-frame">
                    <iframe
                      src={`https://www.youtube.com/embed/${video.video_id}?start=${video.start_seconds}&end=${video.end_seconds}&playsinline=1&rel=0`}
                      title={video.title}
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                      allowFullScreen
                    />
                  </div>
                )}

                <a
                  className="text-button"
                  href={video.watch_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Watch on YouTube
                  <ExternalLink size={14} />
                </a>
              </article>
            ))}
          </div>
        </div>
      )}

      {!videos.length &&
        !searchResults.length &&
        !selectedVideo && (
          <div className="empty-state">
            <BarChart3 size={24} />
            <p>
              Search for a video related to{" "}
              <strong>{topic}</strong> to get started.
            </p>
          </div>
        )}
    </section>
  );
}