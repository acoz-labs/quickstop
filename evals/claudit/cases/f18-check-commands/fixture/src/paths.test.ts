import { expect, test } from 'bun:test';
import { join, stem } from './paths';

test('join collapses slashes', () => {
  expect(join('a/', '/b', 'c')).toBe('a/b/c');
});

test('stem drops the last extension', () => {
  expect(stem('dir/report.final.md')).toBe('report.final');
});
