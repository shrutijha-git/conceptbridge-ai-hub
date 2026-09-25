import { LoaderCircle } from "lucide-react";

export function ErrorBox({ text }: { text: string }) {
  return text ? (
    <div className="error-box" role="alert">
      {text}
    </div>
  ) : null;
}

export function BusyLabel({ text }: { text: string }) {
  return (
    <span className="inline">
      <LoaderCircle size={16} className="spin" aria-hidden="true" />
      {text}
    </span>
  );
}
