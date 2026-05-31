import type { FC, ReactNode, HTMLAttributes, AnchorHTMLAttributes, TableHTMLAttributes, TdHTMLAttributes } from "react";

type HProps = HTMLAttributes<HTMLHeadingElement>;
type PProps = HTMLAttributes<HTMLParagraphElement>;
type UlProps = HTMLAttributes<HTMLUListElement>;
type OlProps = HTMLAttributes<HTMLOListElement>;
type LiProps = HTMLAttributes<HTMLLIElement>;
type BlockquoteProps = HTMLAttributes<HTMLQuoteElement>;
type PreProps = HTMLAttributes<HTMLPreElement>;
type TableProps = TableHTMLAttributes<HTMLTableElement>;
type ThProps = HTMLAttributes<HTMLTableCellElement>;
type TdProps = TdHTMLAttributes<HTMLTableCellElement>;
type HrProps = HTMLAttributes<HTMLHRElement>;
type AProps = AnchorHTMLAttributes<HTMLAnchorElement>;
type CodeProps = HTMLAttributes<HTMLElement> & { "data-language"?: string };

export const mdxComponents = {
  h1: (props: HProps) => <h1 className="text-3xl font-semibold tracking-tight mb-6 mt-0" {...props} />,
  h2: (props: HProps) => <h2 className="text-xl font-semibold mt-12 mb-4 scroll-mt-24" {...props} />,
  h3: (props: HProps) => <h3 className="text-base font-semibold mt-8 mb-3" {...props} />,
  h4: (props: HProps) => <h4 className="text-sm font-semibold mt-6 mb-2 text-muted-foreground" {...props} />,
  p: (props: PProps) => <p className="leading-7 mb-4 text-[15px]" {...props} />,
  ul: (props: UlProps) => <ul className="pl-6 mb-4 space-y-1.5 text-[15px] list-disc" {...props} />,
  ol: (props: OlProps) => <ol className="pl-6 mb-4 space-y-1.5 text-[15px] list-decimal" {...props} />,
  li: (props: LiProps) => <li {...props} />,
  blockquote: (props: BlockquoteProps) => <blockquote className="border-l-2 border-border pl-4 my-6 italic text-muted-foreground" {...props} />,
  code: ({ children, ...props }: CodeProps) => {
    if (props["data-language"]) return <code {...props}>{children}</code>;
    return <code className="font-mono text-[0.875em] px-1.5 py-0.5 rounded bg-muted text-foreground" {...props}>{children}</code>;
  },
  pre: ({ "data-language": dataLanguage, ...props }: PreProps & { "data-language"?: string }) => {
    if (dataLanguage) {
      return <pre className="overflow-x-auto py-4 px-4 text-[13px] leading-6 font-mono" data-language={dataLanguage} {...props} />;
    }
    return <pre className="my-6 overflow-x-auto rounded-md border py-4 px-4 text-[13px] leading-6 font-mono" {...props} />;
  },
  figure: (props: HTMLAttributes<HTMLElement>) => {
    if ("data-rehype-pretty-code-figure" in props) {
      return <figure className="my-6 overflow-hidden rounded-md border text-[13px]" {...props} />;
    }
    return <figure {...props} />;
  },
  table: (props: TableProps) => <table className="my-6 w-full text-[14px] border-collapse" {...props} />,
  th: (props: ThProps) => <th className="border-b border-border px-3 py-2 text-left font-medium" {...props} />,
  td: (props: TdProps) => <td className="border-b border-border/60 px-3 py-2 align-top" {...props} />,
  hr: (props: HrProps) => <hr className="my-10 border-border" {...props} />,
  a: (props: AProps) => <a className="underline underline-offset-4 decoration-muted-foreground/40 hover:decoration-foreground transition-colors" {...props} />,
};

export const Prose: FC<{ children: ReactNode }> = ({ children }) => {
  return <div className="mx-auto max-w-3xl px-8 py-12">{children}</div>;
};
