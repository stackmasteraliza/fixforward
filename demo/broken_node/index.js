/**
 * Simple string utilities module.
 */

function capitalize(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function reverse(str) {
  if (!str) return "";
  return str.split("").reverse().join("");
}

function truncate(str, maxLength) {
  if (!str) return "";
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 3) + "..";  // Bug: should be "..." (3 dots)
}

module.exports = { capitalize, reverse, truncate };
