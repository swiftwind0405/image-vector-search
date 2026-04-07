import { useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import ImageBrowser from "@/components/ImageBrowser";
import { useTags } from "@/api/tags";

export default function TagImagesPage() {
  const { tagId } = useParams();
  const navigate = useNavigate();
  const parsedTagId = Number(tagId);
  const { data: tags } = useTags();

  const tag = useMemo(
    () => (tags ?? []).find((item) => item.id === parsedTagId),
    [tags, parsedTagId],
  );

  if (!Number.isInteger(parsedTagId) || parsedTagId <= 0) {
    return <p className="text-sm text-muted-foreground">Invalid tag id.</p>;
  }

  const displayName = tag ? tag.name : `Tag #${parsedTagId}`;

  return (
    <ImageBrowser
      title={displayName}
      breadcrumb={
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="-ml-2 gap-1 text-muted-foreground"
            onClick={() => navigate("/tags")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-lg font-semibold">{displayName}</h1>
        </div>
      }
      hideTitle
      queryScope={{ tagId: parsedTagId }}
      emptyMessage="No images are assigned to this tag yet."
    />
  );
}
