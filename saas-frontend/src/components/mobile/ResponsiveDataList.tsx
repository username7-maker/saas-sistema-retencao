export function ResponsiveDataList({ cards, table, className = "" }: { cards: React.ReactNode; table: React.ReactNode; className?: string }) {
  return <div className={className}><div className="space-y-3 md:hidden">{cards}</div><div className="hidden overflow-x-auto md:block">{table}</div></div>;
}
