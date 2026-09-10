import { BookOpen } from "lucide-react";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { type SkillInfo, api } from "../lib/api";

export default function Skills() {
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");

  useEffect(() => {
    api.skills().then((r) => {
      setSkills(r.items);
      if (r.items[0]) setSelected(r.items[0].name);
    });
  }, []);

  useEffect(() => {
    if (selected) api.skillContent(selected).then(setContent);
  }, [selected]);

  return (
    <div className="grid grid-cols-4 gap-4" data-testid="skills-page">
      <div className="col-span-1 space-y-1">
        {skills.map((s) => (
          <button
            type="button"
            key={s.name}
            onClick={() => setSelected(s.name)}
            data-testid={`skill-item-${s.name}`}
            className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm ${
              selected === s.name
                ? "bg-amber-500/10 text-amber-400"
                : "text-zinc-400 hover:bg-zinc-800"
            }`}
          >
            <BookOpen size={16} />
            {s.name}
          </button>
        ))}
      </div>
      <div className="prose prose-invert col-span-3 max-w-none rounded-lg border border-zinc-800 bg-panel p-6">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
}
