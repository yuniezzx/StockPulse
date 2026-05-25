import { defineConfig } from "vite";
import mdx from "@mdx-js/rollup";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";
import remarkMath from "remark-math";
import rehypeSlug from "rehype-slug";
import rehypeAutolinkHeadings from "rehype-autolink-headings";
import rehypePrettyCode from "rehype-pretty-code";
import rehypeKatex from "rehype-katex";
import { createHighlighter } from "shiki";

const highlighter = await createHighlighter({
  langs: ["python", "typescript", "tsx", "javascript", "sql", "bash", "json"],
  themes: ["min-light", "min-dark"],
});

export default defineConfig({
  plugins: [
    mdx({
      jsxImportSource: "react",
      remarkPlugins: [remarkMath],
      rehypePlugins: [
        rehypeSlug,
        [rehypeAutolinkHeadings, { behavior: "wrap" }],
        [
          rehypePrettyCode,
          {
            theme: { light: "min-light", dark: "min-dark" },
            keepBackground: false,
            getHighlighter: () => highlighter,
          },
        ],
        rehypeKatex,
      ],
    }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      src: path.resolve(__dirname, "./src"),
    },
  },
});
