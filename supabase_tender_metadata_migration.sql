alter table tenders
  add column if not exists extracted_pdf_path text,
  add column if not exists format_count integer,
  add column if not exists detected_format_types text[],
  add column if not exists detection_method text,
  add column if not exists normalisation_applied boolean;
