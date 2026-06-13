import { useEventCalendar } from '../../hooks/useEventCalendar';
import { useState } from 'react';
import SignalDetailDrawer from '../signals/SignalDetailDrawer';
import type { CalendarEvent } from '../../types/intelligence';
import type { SignalFeedItem } from '../../types/intelligence';
import { apiGet } from '../../api/client';

const COMPANY_COLORS = [
  'bg-blue-100 text-blue-700',
  'bg-green-100 text-green-700',
  'bg-purple-100 text-purple-700',
  'bg-orange-100 text-orange-700',
  'bg-pink-100 text-pink-700',
  'bg-yellow-100 text-yellow-800',
  'bg-teal-100 text-teal-700',
  'bg-red-100 text-red-700',
];

const companyColorCache: Record<string, string> = {};
let colorIndex = 0;

function getCompanyColor(companyId: string): string {
  if (!companyColorCache[companyId]) {
    companyColorCache[companyId] = COMPANY_COLORS[colorIndex % COMPANY_COLORS.length];
    colorIndex++;
  }
  return companyColorCache[companyId];
}

function formatEventDate(isoDate: string): string {
  const d = new Date(isoDate + 'T00:00:00');
  return d.toLocaleDateString('de-DE', { day: 'numeric', month: 'short', year: 'numeric' });
}

function daysFromNow(isoDate: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const eventDate = new Date(isoDate + 'T00:00:00');
  return Math.round((eventDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

interface EventRowProps {
  event: CalendarEvent;
  isPast: boolean;
  onSelect: (signalId: string) => void;
}

function EventRow({ event, isPast, onSelect }: EventRowProps) {
  const days = daysFromNow(event.event_date);
  const daysLabel = isPast
    ? `vor ${Math.abs(days)} Tagen`
    : days === 0
    ? 'Heute'
    : days === 1
    ? 'Morgen'
    : `in ${days} Tagen`;

  return (
    <div
      className={`flex items-start gap-3 cursor-pointer group ${isPast ? 'opacity-55' : ''}`}
      onClick={() => {
        const topSignalId = event.attendees[0]?.signal_id;
        if (topSignalId) onSelect(topSignalId);
      }}
    >
      {/* Date column */}
      <div className="w-[88px] flex-shrink-0 text-right pt-0.5">
        <div className={`text-[11px] font-semibold ${isPast ? 'text-slate-400' : 'text-slate-700'}`}>
          {formatEventDate(event.event_date)}
        </div>
        <div className={`text-[10px] ${isPast ? 'text-slate-300' : 'text-blue-500'}`}>
          {daysLabel}
        </div>
      </div>

      {/* Dot */}
      <div className="flex flex-col items-center flex-shrink-0 mt-1">
        <div
          className={`w-2.5 h-2.5 rounded-full border-2 border-white shadow-sm ${
            isPast ? 'bg-slate-300' : 'bg-blue-500'
          }`}
        />
      </div>

      {/* Content */}
      <div
        className={`flex-1 min-w-0 pb-4 border-b border-slate-100 group-last:border-0 group-hover:bg-slate-50 rounded-lg px-2 -mx-2 transition-colors`}
      >
        <div className={`text-[12px] font-semibold truncate ${isPast ? 'text-slate-400' : 'text-slate-800'}`}>
          {event.title}
        </div>
        {event.event_location && (
          <div className={`text-[11px] mb-1.5 ${isPast ? 'text-slate-300' : 'text-slate-500'}`}>
            {event.event_location}
          </div>
        )}
        <div className="flex flex-wrap gap-1.5">
          {event.attendees.map((a) => (
            <span
              key={a.company_id}
              className={`inline-flex items-center text-[10px] font-medium px-1.5 py-0.5 rounded ${
                isPast ? 'bg-slate-100 text-slate-400' : getCompanyColor(a.company_id)
              }`}
            >
              {a.company_name}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function EventTimelinePanel() {
  const { data, isLoading } = useEventCalendar();
  const [selectedSignal, setSelectedSignal] = useState<SignalFeedItem | null>(null);

  async function handleSelectSignal(signalId: string) {
    try {
      const signal = await apiGet<SignalFeedItem>(`/intelligence/signals/${signalId}`);
      setSelectedSignal(signal);
    } catch {
      // ignore
    }
  }

  const upcoming = data?.upcoming ?? [];
  const past = data?.past ?? [];
  const hasEvents = upcoming.length > 0 || past.length > 0;

  return (
    <>
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-bold text-slate-900 uppercase tracking-wide">Event-Kalender</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Wettbewerber-Events · Upcoming & letzte 30 Tage</div>
          </div>
          {upcoming.length > 0 && (
            <span className="text-[10px] font-semibold text-blue-600 bg-blue-50 rounded-full px-2 py-0.5">
              {upcoming.length} bevorstehend
            </span>
          )}
        </div>

        <div className="px-4 py-4">
          {isLoading && (
            <div className="text-[12px] text-slate-400 text-center py-6">Lade Events…</div>
          )}

          {!isLoading && !hasEvents && (
            <div className="text-[12px] text-slate-400 text-center py-6">
              Keine Events gefunden. Events werden beim nächsten Crawl extrahiert.
            </div>
          )}

          {!isLoading && hasEvents && (
            <div className="relative">
              {/* Vertical timeline line */}
              <div className="absolute left-[95px] top-0 bottom-0 w-px bg-slate-100" />

              <div className="space-y-0 pl-[95px]">
                {upcoming.length > 0 && (
                  <>
                    {/* TODAY marker */}
                    <div className="flex items-center gap-3 mb-3 -ml-[95px]">
                      <div className="w-[88px] text-right">
                        <span className="text-[10px] font-bold text-red-500 uppercase tracking-wide">Heute</span>
                      </div>
                      <div className="w-2.5 h-2.5 rounded-full bg-red-500 border-2 border-white shadow flex-shrink-0" />
                      <div className="text-[10px] text-red-400">
                        {new Date().toLocaleDateString('de-DE', { day: 'numeric', month: 'short', year: 'numeric' })}
                      </div>
                    </div>

                    <div className="space-y-2">
                      {upcoming.map((event) => (
                        <EventRow
                          key={`${event.event_date}-${event.title}`}
                          event={event}
                          isPast={false}
                          onSelect={handleSelectSignal}
                        />
                      ))}
                    </div>
                  </>
                )}

                {past.length > 0 && (
                  <>
                    {upcoming.length === 0 && (
                      <div className="flex items-center gap-3 mb-3 -ml-[95px]">
                        <div className="w-[88px] text-right">
                          <span className="text-[10px] font-bold text-red-500 uppercase tracking-wide">Heute</span>
                        </div>
                        <div className="w-2.5 h-2.5 rounded-full bg-red-500 border-2 border-white shadow flex-shrink-0" />
                        <div className="text-[10px] text-red-400">
                          {new Date().toLocaleDateString('de-DE', { day: 'numeric', month: 'short', year: 'numeric' })}
                        </div>
                      </div>
                    )}
                    <div className="mt-4 pt-3 border-t border-slate-100">
                      <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide mb-3 -ml-[95px] pl-[103px]">
                        Letzte 30 Tage
                      </div>
                      <div className="space-y-2">
                        {past.map((event) => (
                          <EventRow
                            key={`${event.event_date}-${event.title}`}
                            event={event}
                            isPast={true}
                            onSelect={handleSelectSignal}
                          />
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {selectedSignal && (
        <SignalDetailDrawer item={selectedSignal} onClose={() => setSelectedSignal(null)} />
      )}
    </>
  );
}
