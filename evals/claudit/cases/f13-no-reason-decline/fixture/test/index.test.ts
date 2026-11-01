import { test } from "node:test";
import assert from "node:assert";
import { slugify } from "../src/index";

test("slugify", () => assert.equal(slugify("Hello, World"), "hello-world"));
