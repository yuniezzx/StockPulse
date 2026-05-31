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

export default function PortfolioPage() {
  return (
    <FeaturePlaceholder
      title="持仓"
      subtitle="④ Portfolio · /portfolio"
      description="管理真实持仓，追踪盈亏与最大回撤。"
    />
  );
}
