"use client";

import { useState, useRef } from "react";
import { documentsApi, DocumentRecord } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Loader2, Trash2, Upload, FileText } from "lucide-react";

interface Props {
  documents: DocumentRecord[];
  onDocumentsChange: () => void;
  onAnalyzeComplete: () => void;
}

const STATUS_LABELS: Record<string, string> = {
  PENDING: "Pending",
  EXTRACTED: "Text extracted",
  ANALYZED: "Analyzed",
  FAILED: "Failed",
};

const STATUS_COLORS: Record<string, string> = {
  PENDING: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  EXTRACTED: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  ANALYZED: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  FAILED: "bg-red-500/20 text-red-400 border-red-500/30",
};

export function DocumentUploadSection({
  documents,
  onDocumentsChange,
  onAnalyzeComplete,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [docType, setDocType] = useState<string>("RESUME");
  const [targetContext, setTargetContext] = useState("");
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      await documentsApi.upload(
        file,
        docType,
        docType === "COVER_LETTER" && targetContext ? targetContext : undefined
      );
      onDocumentsChange();
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Upload failed. Check file type (PDF/DOCX, max 10MB).";
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      await documentsApi.remove(docId);
      onDocumentsChange();
    } catch {
      setError("Failed to delete document.");
    }
  };

  const handleAnalyze = async () => {
    setError(null);
    setAnalyzing(true);
    try {
      await documentsApi.analyze();
      setTimeout(() => {
        setAnalyzing(false);
        onAnalyzeComplete();
      }, 3000);
    } catch {
      setError("Analysis failed. Please try again.");
      setAnalyzing(false);
    }
  };

  const hasExtracted = documents.some(
    (d) =>
      d.extraction_status === "EXTRACTED" || d.extraction_status === "ANALYZED"
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">Documents</h3>
        {hasExtracted && (
          <Button
            size="sm"
            variant="outline"
            onClick={handleAnalyze}
            disabled={analyzing}
            className="border-violet-500/30 text-violet-400 hover:bg-violet-500/10"
          >
            {analyzing ? (
              <>
                <Loader2 className="mr-2 h-3 w-3 animate-spin" /> Analyzing…
              </>
            ) : (
              "Analyze my profile"
            )}
          </Button>
        )}
      </div>

      {/* Upload zone */}
      <div className="flex gap-3 items-start flex-wrap">
        <Select value={docType} onValueChange={(v) => { if (v) setDocType(v); }}>
          <SelectTrigger className="w-40 h-9 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="RESUME">Resume</SelectItem>
            <SelectItem value="COVER_LETTER">Cover Letter</SelectItem>
          </SelectContent>
        </Select>

        {docType === "COVER_LETTER" && (
          <Input
            placeholder='e.g. "PE firms"'
            value={targetContext}
            onChange={(e) => setTargetContext(e.target.value)}
            className="h-9 text-sm flex-1 min-w-[160px]"
          />
        )}

        <Button
          size="sm"
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="h-9"
        >
          {uploading ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <>
              <Upload className="mr-2 h-3 w-3" /> Upload PDF/DOCX
            </>
          )}
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {/* Document list */}
      {documents.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          No documents uploaded. Upload your resume to enrich your career
          profile.
        </p>
      ) : (
        <ul className="space-y-2">
          {documents.map((doc) => (
            <li
              key={doc.id}
              className="flex items-center gap-3 p-3 rounded-lg bg-card border border-border"
            >
              <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
              <span className="flex-1 text-sm truncate">{doc.filename}</span>
              {doc.target_context && (
                <span className="text-xs text-muted-foreground">
                  {doc.target_context}
                </span>
              )}
              <Badge
                variant="outline"
                className={`text-xs ${STATUS_COLORS[doc.extraction_status] ?? ""}`}
              >
                {STATUS_LABELS[doc.extraction_status] ?? doc.extraction_status}
              </Badge>
              <button
                onClick={() => handleDelete(doc.id)}
                className="text-muted-foreground hover:text-red-400 transition-colors"
                aria-label="Delete document"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
