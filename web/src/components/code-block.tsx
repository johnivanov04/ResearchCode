import { CopyButton } from "@/components/copy-button";

type CodeBlockProps = {
  code: string;
  language?: string;
  /** Short label shown in the header bar, such as a file name. */
  title?: string;
  caption?: string;
  copyable?: boolean;
};

export function CodeBlock({ code, language, title, caption, copyable = true }: CodeBlockProps) {
  return (
    <figure className="my-6 overflow-hidden rounded-lg border border-navy-800 bg-navy-950">
      <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-2">
        <span className="font-mono text-xs text-navy-200">{title ?? language ?? "code"}</span>
        {copyable ? <CopyButton text={code} /> : null}
      </div>
      <pre className="overflow-x-auto px-4 py-4 text-[0.8125rem] leading-6 text-slate-100">
        <code className="font-mono">{code}</code>
      </pre>
      {caption ? (
        <figcaption className="border-t border-white/10 px-4 py-2 text-xs text-navy-200">
          {caption}
        </figcaption>
      ) : null}
    </figure>
  );
}
