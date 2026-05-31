function FeaturePlaceholder({ title, subtitle, description }: { title: string; subtitle: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 p-6">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="text-sm text-muted-foreground">{subtitle}</p>
      <p className="text-sm text-muted-foreground max-w-md text-center">
        {description}
      </p>
    </div>
  );
}

export default function EvaluationsPage() {
  return (
    <FeaturePlaceholder
      title="校验报告"
      subtitle="⑤ Evaluations · /evaluations"
      description="策略校验报告：胜率、夏普、最大回撤。"
    />
  );
}
