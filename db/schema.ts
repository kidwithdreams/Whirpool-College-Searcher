import { check, index, integer, primaryKey, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";
import { sql } from "drizzle-orm";

export const users = sqliteTable(
  "users",
  {
    id: text("id").primaryKey(),
    email: text("email").notNull(),
    plan: text("plan", { enum: ["free", "plus", "max"] }).notNull().default("free"),
    billingStatus: text("billing_status").notNull().default("inactive"),
    createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
    weekStartedAt: integer("week_started_at").notNull().default(0),
    weeklySearches: integer("weekly_searches").notNull().default(0),
    totalSearches: integer("total_searches").notNull().default(0),
  },
  (table) => [
    uniqueIndex("idx_users_email").on(table.email),
    check("users_plan_check", sql`${table.plan} in ('free', 'plus', 'max')`),
  ],
);

export const favorites = sqliteTable(
  "favorites",
  {
    userId: text("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
    universityName: text("university_name").notNull(),
    location: text("location").notNull().default(""),
    summary: text("summary").notNull().default(""),
    addedAt: text("added_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [
    primaryKey({ columns: [table.userId, table.universityName] }),
    index("idx_favorites_user_added").on(table.userId, table.addedAt),
  ],
);
