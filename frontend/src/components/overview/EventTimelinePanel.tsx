import { useEventCalendar } from '../../hooks/useEventCalendar';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, ChevronUp, ArrowRight } from 'lucide-react';
import SignalDetailDrawer from '../signals/SignalDetailDrawer';
import CompanyLogo from '../CompanyLogo';
import type { CalendarEvent } from '../../types/intelligence';
import type { SignalFeedItem } from '../../types/intelligence';
import { apiGet } from '../../api/client';
import { useCompanies } from '../../hooks/useCompanies';

type LogoMap = Record<string, { slug: string; logo_path: string | null }>;

const NEW_SIGNAL_HOURS = 7 * 24;

function isNewEvent(newestSignalAt: string | null): boolean {
  if (!newestSignalAt) return false;
  const diffMs = Date.now() - new Date(newestSignalAt).getTime();
  return diffMs < NEW_SIGNAL_HOURS * 60 * 60 * 1000;
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
  logoMap: LogoMap;
}

function EventRow({ event, isPast, onSelect, logoMap }: EventRowProps) {
  const isNew = !isPast && isNewEvent(event.newest_signal_at);
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
      <div className="w-[70px] flex-shrink-0 text-right pt-0.5">
        <div className={`text-[11px] font-semibold ${isPast ? 'text-slate-400' : 'text-slate-700'}`}>
          {formatEventDate(event.event_date)}
        </div>
        <div className={`text-[10px] ${isPast ? 'text-slate-300' : 'text-blue-500'}`}>
          {daysLabel}
        </div>
      </div>

      {/* Content */}
      <div
        className={`flex-1 min-w-0 pb-4 border-b border-slate-100 group-last:border-0 group-hover:bg-slate-50 rounded-lg px-2 -mx-2 transition-colors`}
      >
        <div className={`flex items-center gap-1.5 flex-wrap ${isPast ? 'opacity-60' : ''}`}>
          {event.attendees.map((a, i) => {
            const logo = logoMap[a.company_id];
            return (
              <div key={a.company_id} className="flex items-center gap-1 flex-shrink-0">
                {i > 0 && <span className={`text-[11px] ${isPast ? 'text-slate-300' : 'text-slate-400'}`}>,</span>}
                <CompanyLogo
                  name={a.company_name}
                  slug={logo?.slug ?? a.company_slug}
                  logo_path={logo?.logo_path ?? null}
                  size="sm"
                  companyId={a.company_id}
                />
                <span className={`text-[11px] font-medium ${isPast ? 'text-slate-400' : 'text-slate-600'}`}>
                  {a.company_name}
                </span>
              </div>
            );
          })}
          <div className={`text-[12px] font-semibold truncate ${isPast ? 'text-slate-400' : 'text-slate-800'}`}>
            {event.event_name || event.title}
          </div>
          {isNew && (
            <span className="flex items-center gap-0.5 text-[10px] font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded-full flex-shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
              Neu
            </span>
          )}
          {event.event_type && (
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full flex-shrink-0 ${isPast ? 'bg-slate-100 text-slate-400' : 'bg-violet-100 text-violet-600'}`}>
              {event.event_type}
            </span>
          )}
        </div>
        {event.event_location && (
          <div className={`text-[11px] mt-0.5 ${isPast ? 'text-slate-300' : 'text-slate-500'}`}>
            {event.event_location}
          </div>
        )}
      </div>
    </div>
  );
}

const PAST_COLLAPSED_LIMIT = 2;
const UPCOMING_NEAR_DAYS = 30;

interface EventTimelinePanelProps {
  fullView?: boolean;
}

export default function EventTimelinePanel({ fullView = false }: EventTimelinePanelProps) {
  const { data, isLoading } = useEventCalendar(fullView);
  const [selectedSignal, setSelectedSignal] = useState<SignalFeedItem | null>(null);
  const [pastExpanded, setPastExpanded] = useState(false);

  async function handleSelectSignal(signalId: string) {
    try {
      const signal = await apiGet<SignalFeedItem>(`/intelligence/signals/${signalId}`);
      setSelectedSignal(signal);
    } catch {
      // ignore
    }
  }

  const { data: companies } = useCompanies();
  const logoMap: LogoMap = Object.fromEntries(
    (companies ?? []).map((c) => [c.id, { slug: c.slug, logo_path: c.logo_path }])
  );

  const upcoming = data?.upcoming ?? [];
  const past = data?.past ?? [];
  const hasEvents = upcoming.length > 0 || past.length > 0;
  const visiblePast = fullView && pastExpanded ? past : past.slice(0, PAST_COLLAPSED_LIMIT);
  const upcomingNear = fullView ? upcoming : upcoming.filter((e) => daysFromNow(e.event_date) <= UPCOMING_NEAR_DAYS);

  return (
    <>
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-bold text-slate-900 uppercase tracking-wide">Event-Kalender</div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              Wettbewerber-Events · {fullView ? 'Gesamte Historie' : 'Bevorstehende Events'}
            </div>
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
            <div>

              {/* Past events — above Heute */}
              {fullView && past.length > 0 && (
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">
                      {fullView ? 'Vergangene Events' : 'Letzte 30 Tage'}
                    </div>
                    {fullView && past.length > PAST_COLLAPSED_LIMIT && (
                      <button
                        onClick={() => setPastExpanded((v) => !v)}
                        className="flex items-center gap-0.5 text-[10px] text-slate-400 hover:text-slate-600 transition-colors"
                      >
                        {pastExpanded ? (
                          <><ChevronUp size={11} /> Weniger</>
                        ) : (
                          <><ChevronDown size={11} /> +{past.length - PAST_COLLAPSED_LIMIT} weitere</>
                        )}
                      </button>
                    )}
                  </div>
                  <div className="space-y-2">
                    {visiblePast.map((event) => (
                      <EventRow
                        key={`${event.event_date}-${event.title}`}
                        event={event}
                        isPast={true}
                        onSelect={handleSelectSignal}
                        logoMap={logoMap}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* TODAY divider */}
              <div className="flex items-center gap-2 my-3">
                <span className="text-[10px] font-bold text-red-500 uppercase tracking-wide">Heute</span>
                <span className="text-[10px] text-slate-400">
                  {new Date().toLocaleDateString('de-DE', { day: 'numeric', month: 'short', year: 'numeric' })}
                </span>
                <div className="flex-1 border-t border-slate-100" />
              </div>

              {/* Upcoming events — below Heute */}
              {upcoming.length === 0 ? (
                <div className="text-[11px] text-slate-300 italic pb-2">Keine bevorstehenden Events</div>
              ) : (
                <div className="space-y-2">
                  {upcomingNear.map((event) => (
                    <EventRow
                      key={`${event.event_date}-${event.title}`}
                      event={event}
                      isPast={false}
                      onSelect={handleSelectSignal}
                      logoMap={logoMap}
                    />
                  ))}
                </div>
              )}

            </div>
          )}
        </div>

        {!fullView && (
          <Link
            to="/events"
            className="flex items-center justify-center gap-1 text-[11px] font-medium text-blue-600 hover:text-blue-700 border-t border-slate-100 px-4 py-2.5 transition-colors"
          >
            Alle Events ansehen <ArrowRight size={12} />
          </Link>
        )}
      </div>

      {selectedSignal && (
        <SignalDetailDrawer item={selectedSignal} onClose={() => setSelectedSignal(null)} />
      )}
    </>
  );
}
