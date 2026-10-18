export type FieldObservation = {
  path: string;
  types: string[];
  nullable: boolean;
  isoTimestamp: boolean;
};

const SENSITIVE_KEY = /token|secret|authorization|password|email|phone|address|name|accountid|accountkey|clientkey|clientid|userid|userkey|counterpart|ownerid/i;

/** Field catalogue only. Values, including identifiers, are not retained. */
export function catalogueJson(value: unknown): FieldObservation[] {
  const map = new Map<string, FieldObservation>();
  walk(value, "$", map);
  return [...map.values()];
}

function walk(value: unknown, path: string, map: Map<string, FieldObservation>): void {
  const existing = map.get(path) ?? {
    path,
    types: [],
    nullable: false,
    isoTimestamp: false,
  };
  const kind = value === null ? "null" : Array.isArray(value) ? "array" : typeof value;
  if (!existing.types.includes(kind)) existing.types.push(kind);
  if (value === null) existing.nullable = true;
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value)) existing.isoTimestamp = true;
  map.set(path, existing);

  if (Array.isArray(value)) {
    for (const item of value) walk(item, `${path}[]`, map);
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    if (SENSITIVE_KEY.test(key)) {
      const childPath = `${path}.${key}`;
      const noted = map.get(childPath) ?? {
        path: childPath,
        types: [],
        nullable: child === null,
        isoTimestamp: false,
      };
      const childKind = child === null ? "null" : Array.isArray(child) ? "array" : typeof child;
      if (!noted.types.includes(childKind)) noted.types.push(childKind);
      noted.nullable = noted.nullable || child === null;
      map.set(childPath, noted);
      continue;
    }
    walk(child, `${path}.${key}`, map);
  }
}
