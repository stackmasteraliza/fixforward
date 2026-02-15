const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const { capitalize, reverse, truncate } = require("./index");

describe("capitalize", () => {
  it("capitalizes the first letter", () => {
    assert.strictEqual(capitalize("hello"), "Hello");
  });

  it("returns empty string for empty input", () => {
    assert.strictEqual(capitalize(""), "");
  });
});

describe("reverse", () => {
  it("reverses a string", () => {
    assert.strictEqual(reverse("hello"), "olleh");
  });

  it("returns empty string for empty input", () => {
    assert.strictEqual(reverse(""), "");
  });
});

describe("truncate", () => {
  it("truncates long strings with ellipsis", () => {
    assert.strictEqual(truncate("Hello World", 8), "Hello...");  // Fails: gets "Hello.."
  });

  it("returns original string if short enough", () => {
    assert.strictEqual(truncate("Hi", 10), "Hi");
  });
});
