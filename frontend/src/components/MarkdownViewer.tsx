import ReactMarkdown from 'react-markdown';

interface MarkdownViewerProps {
  content: string;
}

export default function MarkdownViewer({ content }: MarkdownViewerProps) {
  return (
    <div className="prose prose-sm max-w-none text-slate-800">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
