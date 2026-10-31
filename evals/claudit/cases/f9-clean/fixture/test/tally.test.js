import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tally } from '../src/tally.js';

test('counts words', () => assert.equal(tally('One, two; three.'), 3));
test('empty text', () => assert.equal(tally(''), 0));
