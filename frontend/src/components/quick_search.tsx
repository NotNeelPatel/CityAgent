import { Button } from "@/components/ui/button";

const QuickSearchs = [
  { questions: "What is the pavement condition rating of the road segment on Baseline Road from Woodroffe to Highgate?", href: "#" },
  { questions: "What is the Pavement Quality Index (PQI) values for all road segments for Bank Street?", href: "#" },
  { questions: "Which ward is the road segment on Carling Avenue located in?", href: "#" },
  { questions: "What functional road class is assigned to the road segment on Hunt Club Road?", href: "#" },
  { questions: "What is the total replacement cost of the road segment on St. Laurent Boulevard?", href: "#" },
  { questions: "How many lane kilometers does the road segment on Merivale Road have?", href: "#" },
];

type QuickSearchItemProps = {
  onSubmit: (q: string) => void;
  setQuery: (q: string) => void;
};

const QuickSearchItem = ({ onSubmit, setQuery }: QuickSearchItemProps) => {
  return (
    <div className="grid w-full grid-cols-3 gap-4">
      {QuickSearchs.map((item, idx) => (
        <Button
          key={idx}
          variant="secondary"
          className="h-auto items-start justify-start whitespace-normal break-words text-left"
          asChild
        >
          <a
            href={item.href}
            onClick={(e) => {
              e.preventDefault();
              setQuery(item.questions);
              onSubmit(item.questions);
            }}
          >
            {item.questions}
          </a>
        </Button>
      ))}
    </div>

  );
};

export { QuickSearchItem };