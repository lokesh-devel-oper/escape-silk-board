import "@testing-library/jest-dom/vitest";
import { beforeEach } from "vitest";

Object.defineProperty(Element.prototype, "scrollIntoView", {
  configurable: true,
  value: () => undefined,
});

beforeEach(() => {
  localStorage.clear();
});
