export { subjects, lessons } from './library.mjs';
import { subjects, lessons } from './library.mjs';

export function normalizeSearch(value) {
  return value.normalize('NFKD').replace(/[̀-ًͯ-ٰٟـ]/g, '').replace(/[أإآ]/g, 'ا').toLowerCase().trim();
}

export function matchesLesson(lesson, query = '', subject = 'all', category = 'lesson', format = 'all') {
  const subjectInfo = subjects.find(item => item.id === lesson.subject);
  const searchable = normalizeSearch([lesson.title.en, lesson.title.ar, subjectInfo?.en, subjectInfo?.ar, ...lesson.attachments.map(item => item.name)].join(' '));
  return (subject === 'all' || lesson.subject === subject) && lesson.category === category && (format === 'all' || lesson.format === format) && normalizeSearch(query).split(/\s+/).every(term => searchable.includes(term));
}

export const mediaUrl = key => '/media/' + key.split('/').map(encodeURIComponent).join('/');

export function formatSize(bytes) {
  return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : bytes >= 1e6 ? `${Math.round(bytes / 1e6)} MB` : `${Math.max(1, Math.round(bytes / 1e3))} KB`;
}

export function countTypes(lesson) {
  const counts = {};
  for (const item of lesson.attachments) counts[item.type] = (counts[item.type] || 0) + 1;
  return counts;
}
