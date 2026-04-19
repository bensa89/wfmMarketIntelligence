import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useCompany } from '../hooks/useCompanies';
import { useSignals } from '../hooks/useSignals';
import { useDocument } from '../hooks/useDocuments';
import SignalCard from '../components/SignalCard';
import FilterBar from '../components/FilterBar';
import MarkdownViewer from '../components/MarkdownViewer';
import type { SignalType } from '../types';
import { ArrowLeft } from 'lucide-react';

export default function CompetitorDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { data: company, isLoading: companyLoading } = useCompany(slug!);
  const [signalType, setSignalType] = useState<SignalType | ''>('');
  const [minRelevance, setMinRelevance] = useState(0);

  const { data: signals, isLoading: signalsLoading } = useSignals(
    company
      ? {
          company_id: company.id,
          signal_type: signalType || undefined,
          min_relevance: minRelevance || undefined,
        }
      : undefined,
  );

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  if (companyLoading) return <p className="text-dark-muted">Loading...</p>;
  if (!company) return <p className="text-signal-low">Company not found.</p>;

  return (
    <div>
      <Link to="/competitors" className="text-sm text-dark-accent hover:underline flex items-center gap-1 mb-4">
        <ArrowLeft size={14} /> Back to list
      </Link>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">{company.name}</h1>
          <p className="text-sm text-dark-muted">
            {company.type === 'competitor' ? 'Competitor' : 'Market Source'}
            {company.website && ` · ${company.website}`}
          </p>
        </div>
        {company.description && (
          <p className="text-sm text-dark-muted max-w-md">{company.description}</p>
        )}
      </div>
      <FilterBar
        signalType={signalType}
        onSignalTypeChange={setSignalType}
        minRelevance={minRelevance}
        onMinRelevanceChange={setMinRelevance}
      />
      {signalsLoading ? (
        <p className="text-dark-muted">Loading signals...</p>
      ) : (
        <div className="space-y-4">
          {signals?.map((signal) => (
            <SignalCard
              key={signal.id}
              signal={signal}
              onClick={signal.document_id ? () => setSelectedDocId(signal.document_id) : undefined}
            />
          ))}
          {signals?.length === 0 && (
            <p className="text-dark-muted">No signals found for this company.</p>
          )}
        </div>
      )}
      {selectedDocId && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-8 z-50" onClick={() => setSelectedDocId(null)}>
          <div className="card max-w-3xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">Source Document</h3>
              <button onClick={() => setSelectedDocId(null)} className="text-dark-muted hover:text-dark-text">Close</button>
            </div>
            <DocumentViewer documentId={selectedDocId} />
          </div>
        </div>
      )}
    </div>
  );
}

function DocumentViewer({ documentId }: { documentId: string }) {
  const { data: doc, isLoading } = useDocument(documentId);
  if (isLoading) return <p className="text-dark-muted">Loading document...</p>;
  if (!doc) return <p className="text-signal-low">Document not found.</p>;

  return (
    <div>
      <h4 className="font-medium mb-2">{doc.title || 'Untitled'}</h4>
      <p className="text-xs text-dark-muted mb-4">
        Crawled: {new Date(doc.crawled_at).toLocaleDateString('de-DE')} ·{' '}
        <a href={doc.url} target="_blank" rel="noopener noreferrer" className="text-dark-accent hover:underline">Original URL</a>
      </p>
      {doc.content_markdown ? (
        <MarkdownViewer content={doc.content_markdown} />
      ) : (
        <p className="text-dark-muted">No markdown content available.</p>
      )}
    </div>
  );
}
