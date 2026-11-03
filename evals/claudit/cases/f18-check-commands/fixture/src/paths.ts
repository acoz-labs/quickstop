export function join(...parts: string[]): string {
  return parts.filter(Boolean).join('/').replace(/\/+/g, '/');
}

export function stem(path: string): string {
  const name = path.split('/').pop() ?? '';
  const dot = name.lastIndexOf('.');
  return dot > 0 ? name.slice(0, dot) : name;
}
