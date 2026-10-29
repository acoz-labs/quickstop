# slugsmith

```js
import { slugify } from "slugsmith";
slugify("Größe & Café"); // "groesse-and-cafe"
```

Options: `maxLength` (default 80) cuts at a word boundary; `rules` replaces
the built-in transliteration table.

## Develop

```sh
npm test
npm run lint
```

Conventions are in [docs/conventions.md](docs/conventions.md).
