import EventTimelinePanel from '../components/overview/EventTimelinePanel';

export default function EventCalendarPage() {
  return (
    <div className="flex flex-col h-full bg-slate-50">
      <div className="bg-white border-b border-slate-200 px-4 md:px-6 py-3 flex-shrink-0">
        <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">Event-Kalender</h1>
        <p className="text-[12px] text-slate-500 mt-0.5">Alle Wettbewerber-Events</p>
      </div>

      <div className="flex-1 overflow-auto px-4 md:px-6 py-5">
        <EventTimelinePanel fullView />
      </div>
    </div>
  );
}
