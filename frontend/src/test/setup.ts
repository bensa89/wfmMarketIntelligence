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
// oversized and get hidden).
//
// Separately, ResponsiveContainer itself measures its own wrapper div
// (class "recharts-responsive-container") via getBoundingClientRect (not
// offsetWidth/offsetHeight as the stub above might suggest) to size the
// chart on mount, before ResizeObserver ever fires. Give that element the
// same fixed size as the offsetWidth/offsetHeight stub above so charts
// still render.
//
// Every other element falls through to the real (jsdom) implementation,
// so tests that assert genuine layout/visibility via getBoundingClientRect
// aren't given a fabricated non-zero value.
const realGetBoundingClientRect = HTMLElement.prototype.getBoundingClientRect;
HTMLElement.prototype.getBoundingClientRect = function getBoundingClientRect() {
  if (this.id === 'recharts_measurement_span') {
    const width = (this.textContent?.length ?? 0) * 6;
    const height = 14;
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
  }
  if (this.classList?.contains('recharts-responsive-container')) {
    const width = 400;
    const height = 300;
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
  }
  return realGetBoundingClientRect.call(this);
};

if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
