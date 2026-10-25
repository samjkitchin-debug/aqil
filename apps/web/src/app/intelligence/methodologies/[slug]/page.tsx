import { notFound } from "next/navigation";

import { MethodologyRoute } from "@/components/intelligence/methodology-route";
import { METHODOLOGY_CATALOGUE, methodologyBySlug } from "@/lib/research/methodology-catalogue";

export function generateStaticParams() {
  return METHODOLOGY_CATALOGUE.map((entry) => ({ slug: entry.slug }));
}

export default async function MethodologyPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!methodologyBySlug(slug)) notFound();
  return <MethodologyRoute slug={slug} />;
}