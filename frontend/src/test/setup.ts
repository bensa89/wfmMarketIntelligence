import '@testing-library/jest-dom';
import { configure } from '@testing-library/dom';

// recharts keeps a hidden `aria-hidden="true"` span (id="recharts_measurement_span")
// in document.body across renders to measure tick label text. It's invisible to
// real users, so exclude aria-hidden elements from text queries the same way
// script/style are excluded by default, to avoid duplicate-match errors.
configure({ defaultIgnore: 'script, style, [aria-hidden="true"]' });

// recharts' ResponsiveContainer measures its parent via offsetWidth/offsetHeight,
// which jsdom always reports as 0. Without a non-zero size it skips rendering
// its children entirely, so tests can't find chart content. Stub both to a
// reasonable fixed size for all tests.
Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
  configurable: true,
  value: 400,
});
Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
  configurable: true,
  value: 300,
});
// recharts also measures individual tick label text via a hidden
// "recharts_measurement_span" element (getBoundingClientRect) to decide
// which ticks fit and should be shown. Give that element a size based on
// its text content so measurements stay proportional instead of reporting
// a fixed size for every string (which would make all labels look
// oversized and get hidden). All other elements fall back to the fixed
// container size stubbed above.
HTMLElement.prototype.getBoundingClientRect = function getBoundingClientRect() {
  const isMeasurementSpan = this.id === 'recharts_measurement_span';
  const width = isMeasurementSpan ? (this.textContent?.length ?? 0) * 6 : 400;
  const height = isMeasurementSpan ? 14 : 300;
  return {
    width,
    height,
    top: 0,
    left: 0,
    bottom: height,
    right: width,
    x: 0,
    y: 0,
    toJSON() {
      return this;
    },
  } as DOMRect;
};

if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
