import test from 'node:test';
import assert from 'node:assert/strict';
import { lessons, subjects, matchesLesson, normalizeSearch, mediaUrl } from '../src/data/catalog.mjs';

test('real catalog is bilingual, well referenced, and searchable', () => {
  assert.equal(new Set(lessons.map(lesson => lesson.id)).size, lessons.length);
  const keys = lessons.flatMap(lesson => lesson.attachments.map(item => item.key));
  assert.equal(new Set(keys).size, keys.length, 'every file belongs to exactly one lesson');
  for (const lesson of lessons) {
    assert.ok(subjects.some(subject => subject.id === lesson.subject));
    assert.ok(lesson.title.ar && lesson.title.en);
    assert.ok(Number.isInteger(lesson.source) && lesson.source > 0);
    assert.ok(lesson.attachments.length > 0);
    for (const item of lesson.attachments) assert.ok(item.size > 0 && item.key.endsWith(item.name));
  }
  assert.equal(normalizeSearch(' أَسْنَان '), 'اسنان');
  const trauma = lessons.find(lesson => lesson.id === 'surgery-trauma');
  assert.ok(matchesLesson(trauma, 'TRAUMA'));
  assert.ok(matchesLesson(trauma, 'condylar'), 'search reaches file names');
  assert.ok(matchesLesson(trauma, 'إصابات'));
  assert.ok(!matchesLesson(trauma, '', 'anatomy') && !matchesLesson(trauma, 'nonexistent topic'));
  assert.ok(!matchesLesson(trauma, '', 'all', 'reference'));
  assert.ok(lessons.some(lesson => lesson.category === 'reference') && lessons.some(lesson => lesson.category === 'exam'));
  assert.ok(lessons.some(lesson => lesson.id === 'head-neck-anatomy-notes-and-revision'), 'featured lesson exists');
  assert.equal(mediaUrl('Oral Pathology/DC part1.opus'), '/media/Oral%20Pathology/DC%20part1.opus');
});
