import { Callout } from "@/components/callout";
import { Checklist } from "@/components/checklist";
import { CodeBlock } from "@/components/code-block";
import { InlineText } from "@/components/inline-text";
import { PromptBlock } from "@/components/prompt-block";
import type { GuideBlock, GuideSection } from "@/content/guides";

function Block({ block }: { block: GuideBlock }) {
  switch (block.type) {
    case "paragraph":
      return (
        <p>
          <InlineText text={block.text} />
        </p>
      );
    case "list": {
      const ListTag = block.ordered ? "ol" : "ul";
      return (
        <ListTag>
          {block.items.map((item) => (
            <li key={item}>
              <InlineText text={item} />
            </li>
          ))}
        </ListTag>
      );
    }
    case "code":
      return <CodeBlock code={block.code} language={block.language} title={block.title} caption={block.caption} />;
    case "prompt":
      return <PromptBlock title={block.title} prompt={block.prompt} note={block.note} />;
    case "checklist":
      return <Checklist title={block.title} items={block.items} />;
    case "callout":
      return (
        <Callout tone={block.tone} title={block.title}>
          <InlineText text={block.text} />
        </Callout>
      );
  }
}

export function GuideSections({ sections }: { sections: readonly GuideSection[] }) {
  return (
    <div className="prose-rc">
      {sections.map((section) => (
        <section key={section.id} id={section.id} aria-labelledby={`${section.id}-heading`} className="pt-10 first:pt-0">
          <h2 id={`${section.id}-heading`} className="text-2xl font-semibold tracking-tight text-ink">
            {section.title}
          </h2>
          {section.blocks.map((block, index) => (
            <Block key={index} block={block} />
          ))}
        </section>
      ))}
    </div>
  );
}
