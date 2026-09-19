# Data model reference

`schema.ts` contains a Drizzle/SQLite schema explored during development for user
accounts, saved universities, and subscription usage counters.

The hackathon product deliberately has no registration, subscription, payment, or
search-limit flow. This schema is kept as a future-development reference and is not
connected to the deployed application.

Possible next steps are to retain only the `favorites` concept, add anonymous or
optional accounts, and remove the unused billing fields before any production use.
