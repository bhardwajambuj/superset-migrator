import unittest

from sql_schema import extract_cte_names, extract_query_schemas, replace_query_schemas


SCHEMA_MAP = {"dev_analytics": "qa_analytics"}


class CteSchemaRewriteTests(unittest.TestCase):
    def test_plain_from_join(self):
        sql = "SELECT * FROM dev_analytics.events e JOIN dev_analytics.users u ON e.uid = u.id"
        schemas = extract_query_schemas(sql)
        self.assertEqual(schemas, {"dev_analytics"})
        rewritten, count = replace_query_schemas(sql, SCHEMA_MAP)
        self.assertEqual(count, 2)
        self.assertIn("qa_analytics.events", rewritten)
        self.assertIn("qa_analytics.users", rewritten)

    def test_cte_body_from_clause(self):
        sql = """
        WITH daily AS (
            SELECT * FROM dev_analytics.events
        )
        SELECT * FROM daily
        """
        self.assertEqual(extract_cte_names(sql), {"daily"})
        self.assertEqual(extract_query_schemas(sql), {"dev_analytics"})
        rewritten, count = replace_query_schemas(sql, SCHEMA_MAP)
        self.assertEqual(count, 1)
        self.assertIn("qa_analytics.events", rewritten)
        self.assertIn("FROM daily", rewritten)

    def test_multiple_ctes_and_recursive(self):
        sql = """
        WITH RECURSIVE tree AS (
            SELECT id, parent_id FROM dev_analytics.org
            UNION ALL
            SELECT o.id, o.parent_id
            FROM dev_analytics.org o
            JOIN tree t ON o.parent_id = t.id
        ),
        rolled AS (
            SELECT * FROM tree
        )
        SELECT * FROM rolled
        """
        self.assertEqual(extract_cte_names(sql), {"tree", "rolled"})
        rewritten, count = replace_query_schemas(sql, SCHEMA_MAP)
        self.assertEqual(count, 2)
        self.assertEqual(rewritten.count("qa_analytics.org"), 2)
        self.assertIn("JOIN tree t", rewritten)

    def test_cte_column_list(self):
        sql = """
        WITH summary (day, total) AS (
            SELECT day, SUM(n) FROM dev_analytics.metrics GROUP BY 1
        )
        SELECT * FROM summary
        """
        self.assertEqual(extract_cte_names(sql), {"summary"})
        rewritten, count = replace_query_schemas(sql, SCHEMA_MAP)
        self.assertEqual(count, 1)
        self.assertIn("qa_analytics.metrics", rewritten)

    def test_schema_table_column_in_cte_select(self):
        sql = """
        WITH sample AS (
            SELECT dev_analytics.events.id, dev_analytics.events.ts
            FROM other_table
        )
        SELECT * FROM sample
        """
        rewritten, count = replace_query_schemas(sql, SCHEMA_MAP)
        self.assertEqual(count, 2)
        self.assertIn("qa_analytics.events.id", rewritten)
        self.assertIn("qa_analytics.events.ts", rewritten)

    def test_does_not_rewrite_cte_name_matching_schema(self):
        sql = """
        WITH dev_analytics AS (
            SELECT 1 AS id
        )
        SELECT dev_analytics.id FROM dev_analytics
        """
        self.assertEqual(extract_cte_names(sql), {"dev_analytics"})
        self.assertEqual(extract_query_schemas(sql), set())
        rewritten, count = replace_query_schemas(sql, SCHEMA_MAP)
        self.assertEqual(count, 0)
        self.assertEqual(rewritten, sql)

    def test_quoted_identifiers_inside_cte(self):
        sql = "WITH src AS (SELECT * FROM `dev_analytics`.`events`) SELECT * FROM src"
        rewritten, count = replace_query_schemas(sql, SCHEMA_MAP)
        self.assertEqual(count, 1)
        self.assertIn("`qa_analytics`.`events`", rewritten)

    def test_unmapped_schema_unchanged(self):
        sql = "WITH src AS (SELECT * FROM other_schema.events) SELECT * FROM src"
        rewritten, count = replace_query_schemas(sql, SCHEMA_MAP)
        self.assertEqual(count, 0)
        self.assertEqual(rewritten, sql)


if __name__ == "__main__":
    unittest.main()
