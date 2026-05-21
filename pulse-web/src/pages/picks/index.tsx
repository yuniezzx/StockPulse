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

export default function PicksPage() {
  return (
    <FeaturePlaceholder
      title="选股"
      subtitle="② Picks · /picks"
      description="每日傍晚跑出的候选股票，支持按赛道（超短/波段/中线）筛选与共振查看。"
    />
  );
}
