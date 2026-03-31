import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PreferredShiftBadge } from "../components/common/PreferredShiftBadge";

describe("PreferredShiftBadge", () => {
  it("shows an explanatory hint for check-in derived shift", () => {
    render(<PreferredShiftBadge preferredShift="morning" prefix />);

    const badge = screen.getByText("Turno Manha");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute(
      "title",
      "Turno por check-in inferido pelo padrão recente dos horários em que o aluno treina.",
    );
  });

  it("renders nothing when there is no usable shift", () => {
    const { container } = render(<PreferredShiftBadge preferredShift={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
