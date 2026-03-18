import { useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import ImageBrowser from "@/components/ImageBrowser";
import { useTags } from "@/api/tags";

export default function TagImagesPage() {
  const { tagId } = useParams();
  const parsedTagId = Number(tagId);
  const { data: tags, isLoading } = useTags();

  const tag = useMemo(
    () => (tags ?? []).find((item) => item.id === parsedTagId),
    [tags, parsedTagId],
  );

  if (!Number.isInteger(parsedTagId) || parsedTagId <= 0) {
    return <p className="text-sm text-muted-foreground">Invalid tag id.</p>;
  }

  return (
    <ImageBrowser
      title={tag ? `Tag: ${tag.name}` : `Tag #${parsedTagId}`}
      subtitle={
        isLoading ? "Loading tag..." : "Browse images assigned to this tag."
      }
      breadcrumb={
        <nav className="flex items-center gap-1 text-sm text-muted-foreground">
          <Link to="/tags" className="hover:text-foreground transition-colors">
            Tags
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="text-foreground">
            {tag ? tag.name : `#${parsedTagId}`}
          </span>
        </nav>
      }
      queryScope={{ tagId: parsedTagId }}
      emptyMessage="No images are assigned to this tag yet."
    />
  );
}
