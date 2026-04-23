import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownViewerProps {
  content: string;
  className?: string;
}

export default function MarkdownViewer({ content, className = '' }: MarkdownViewerProps) {
  return (
    <div className={`prose prose-sm max-w-none text-slate-800 prose-table:text-[11px] prose-th:border-b prose-th:border-slate-200 prose-th:py-1 prose-th:px-2 prose-th:text-left prose-td:py-1 prose-td:px-2 prose-td:border-b prose-td:border-slate-100 ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
