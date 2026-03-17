import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useImages } from "@/api/images";
import ImageTagEditor from "@/components/ImageTagEditor";
import { ChevronRight, ChevronDown } from "lucide-react";

export default function ImagesPage() {
  const { data: images, isLoading } = useImages();
  const [expandedHash, setExpandedHash] = useState<string | null>(null);

  const toggleExpand = (hash: string) => {
    setExpandedHash((prev) => (prev === hash ? null : hash));
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Images</h1>
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <p className="text-sm text-muted-foreground p-4">Loading...</p>
          ) : !images || images.length === 0 ? (
            <p className="text-sm text-muted-foreground p-4">No images indexed yet</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8" />
                  <TableHead>Content Hash</TableHead>
                  <TableHead>Path</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Size</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {images.map((image) => (
                  <React.Fragment key={image.content_hash}>
                    <TableRow
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => toggleExpand(image.content_hash)}
                    >
                      <TableCell>
                        {expandedHash === image.content_hash ? (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {image.content_hash.slice(0, 16)}...
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                        {image.canonical_path}
                      </TableCell>
                      <TableCell className="text-sm">{image.mime_type}</TableCell>
                      <TableCell className="text-sm">
                        {image.width}x{image.height}
                      </TableCell>
                    </TableRow>
                    {expandedHash === image.content_hash && (
                      <TableRow>
                        <TableCell colSpan={5} className="bg-muted/30 p-0">
                          <ImageTagEditor contentHash={image.content_hash} />
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
