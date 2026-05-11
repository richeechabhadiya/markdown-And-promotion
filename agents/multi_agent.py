import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class AgentOutput:
    agent_name: str
    recommendation: str
    confidence: float
    reasoning: str
    data: Dict[str, Any] = field(default_factory=dict)


class PricingAgent:
    name = "Pricing Agent"
    icon = "💰"

    def analyze(self, product: pd.Series, elasticity: float) -> AgentOutput:
        price = product.get("price", 0)
        special_price = product.get("special_price", 0)
        current_discount = product.get("discount_pct", 0)
        quantity = product.get("quantity", 0)
        abc_class = product.get("abc_class", "C")
        clearance_risk = product.get("clearance_risk", "LOW")
        sell_through = product.get("sell_through_rate", 50)

        # Recommend markdown based on inventory pressure and elasticity
        base_markdown = 0.0
        if clearance_risk == "HIGH":
            base_markdown = 30.0
        elif clearance_risk == "MEDIUM":
            base_markdown = 15.0
        else:
            base_markdown = 5.0

        # Adjust for ABC class
        if abc_class == "A":
            base_markdown *= 0.5  # Protect margin on top products
        elif abc_class == "C":
            base_markdown *= 1.3

        # Adjust for elasticity (more elastic = more markdown helps)
        elasticity_factor = min(abs(elasticity) / 2, 1.5)
        recommended_markdown = base_markdown * elasticity_factor

        # Cap based on sell-through
        if sell_through > 80:
            recommended_markdown = min(recommended_markdown, 5)
        
        recommended_markdown = round(min(recommended_markdown, 60), 1)
        confidence = 0.85 if clearance_risk != "LOW" else 0.65

        reasoning = (
            f"Based on {clearance_risk} clearance risk and {abc_class}-class classification, "
            f"recommend {recommended_markdown:.1f}% markdown. "
            f"Current sell-through is {sell_through:.1f}%. "
            f"Price elasticity of {elasticity:.2f} suggests demand is "
            f"{'highly' if abs(elasticity) > 1.5 else 'moderately'} responsive to price changes."
        )

        return AgentOutput(
            agent_name=self.name,
            recommendation=f"Apply {recommended_markdown:.1f}% markdown",
            confidence=confidence,
            reasoning=reasoning,
            data={
                "recommended_markdown": recommended_markdown,
                "current_discount": current_discount,
                "abc_class": abc_class,
                "clearance_risk": clearance_risk
            }
        )


class InventoryAgent:
    name = "Inventory Agent"
    icon = "📦"

    def analyze(self, product: pd.Series) -> AgentOutput:
        quantity = product.get("quantity", 0)
        sales_velocity = product.get("sales_velocity", 0)
        days_of_stock = product.get("days_of_stock", 9999)
        is_dead = product.get("is_dead_inventory", False)
        inventory_pressure = product.get("inventory_pressure", 0)
        clearance_risk = product.get("clearance_risk", "LOW")

        if is_dead:
            urgency = "CRITICAL"
            recommendation = "Immediate clearance action required"
            confidence = 0.93
        elif clearance_risk == "HIGH":
            urgency = "HIGH"
            recommendation = "Accelerate sell-through via aggressive markdown"
            confidence = 0.88
        elif clearance_risk == "MEDIUM":
            urgency = "MEDIUM"
            recommendation = "Moderate markdown + bundle promotion"
            confidence = 0.75
        else:
            urgency = "LOW"
            recommendation = "Maintain current pricing, monitor velocity"
            confidence = 0.70

        reasoning = (
            f"Current stock: {quantity:.0f} units. "
            f"Sales velocity: {sales_velocity:.3f} units/day. "
            f"Days of stock remaining: {min(days_of_stock, 9999):.0f}. "
            f"Inventory pressure index: {inventory_pressure:.1f}. "
            f"Urgency level: {urgency}."
        )

        return AgentOutput(
            agent_name=self.name,
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning,
            data={
                "urgency": urgency,
                "quantity": quantity,
                "days_of_stock": min(days_of_stock, 9999),
                "is_dead_inventory": bool(is_dead),
                "inventory_pressure": inventory_pressure
            }
        )


class DemandForecastingAgent:
    name = "Demand Forecasting Agent"
    icon = "📈"

    def analyze(self, product: pd.Series, recent_sales_trend: float = 0.0) -> AgentOutput:
        sales_velocity = product.get("sales_velocity", 0)
        total_qty_sold = product.get("total_qty_sold", 0)
        order_count = product.get("order_count", 0)

        # Simulate 30-day forecast with trend
        trend_factor = 1 + recent_sales_trend
        forecast_30d = sales_velocity * 30 * trend_factor
        forecast_90d = sales_velocity * 90 * trend_factor

        if sales_velocity > 0.5:
            demand_outlook = "STRONG"
            confidence = 0.82
        elif sales_velocity > 0.1:
            demand_outlook = "STABLE"
            confidence = 0.72
        else:
            demand_outlook = "WEAK"
            confidence = 0.68

        recommendation = f"Forecasted 30-day demand: {forecast_30d:.0f} units ({demand_outlook})"
        reasoning = (
            f"Historical sales velocity: {sales_velocity:.3f} units/day over {total_qty_sold:.0f} total units sold. "
            f"Order frequency: {order_count:.0f} orders. "
            f"30-day forecast: {forecast_30d:.0f} units. "
            f"90-day forecast: {forecast_90d:.0f} units. "
            f"Demand outlook: {demand_outlook}."
        )

        return AgentOutput(
            agent_name=self.name,
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning,
            data={
                "forecast_30d": round(forecast_30d, 1),
                "forecast_90d": round(forecast_90d, 1),
                "demand_outlook": demand_outlook,
                "sales_velocity": sales_velocity
            }
        )


class PromotionAgent:
    name = "Promotion Agent"
    icon = "🎯"

    def analyze(self, product: pd.Series, markdown_pct: float, elasticity: float) -> AgentOutput:
        price = product.get("price", 0)
        quantity = product.get("quantity", 0)
        sales_velocity = product.get("sales_velocity", 0)
        abc_class = product.get("abc_class", "C")

        # Revenue uplift estimation
        price_reduction_factor = markdown_pct / 100
        demand_uplift = abs(elasticity) * price_reduction_factor
        revenue_uplift_pct = (demand_uplift - price_reduction_factor) * 100
        
        # Margin impact
        cost_estimate = price * 0.55  # Assume 45% gross margin
        new_price = price * (1 - price_reduction_factor)
        new_margin = (new_price - cost_estimate) / (new_price + 1e-9) * 100
        original_margin = (price - cost_estimate) / (price + 1e-9) * 100
        margin_impact = new_margin - original_margin

        # Clearance probability
        clearance_prob = min(50 + demand_uplift * 60 + (quantity < 20) * 20, 98)

        if revenue_uplift_pct > 10:
            strategy = "Flash Sale (48-hour limited)"
        elif markdown_pct > 20:
            strategy = "Clearance Campaign"
        elif abc_class == "A":
            strategy = "Loyalty Member Exclusive"
        else:
            strategy = "Bundle Promotion"

        reasoning = (
            f"At {markdown_pct:.1f}% markdown, estimated demand uplift: {demand_uplift*100:.1f}%. "
            f"Revenue uplift: {revenue_uplift_pct:.1f}%. "
            f"Margin impact: {margin_impact:.1f}pp. "
            f"Clearance probability: {clearance_prob:.0f}%. "
            f"Recommended strategy: {strategy}."
        )

        return AgentOutput(
            agent_name=self.name,
            recommendation=f"{strategy} — {revenue_uplift_pct:.1f}% revenue uplift",
            confidence=0.78,
            reasoning=reasoning,
            data={
                "strategy": strategy,
                "revenue_uplift_pct": round(revenue_uplift_pct, 1),
                "margin_impact": round(margin_impact, 1),
                "clearance_probability": round(clearance_prob, 1),
                "new_price": round(new_price, 2)
            }
        )


class CustomerBehaviorAgent:
    name = "Customer Behavior Agent"
    icon = "👥"

    def analyze(self, cart_abandonment_rate: float, event_data: Dict) -> AgentOutput:
        abandonment = cart_abandonment_rate
        total_sessions = event_data.get("unique_sessions", 0)
        
        if abandonment > 70:
            price_signal = "Price is a major deterrent — recommend markdown"
            confidence = 0.84
            recommendation = "High cart abandonment signals price sensitivity"
        elif abandonment > 50:
            price_signal = "Moderate price sensitivity — test small discount"
            confidence = 0.72
            recommendation = "Moderate abandonment — targeted discount may help"
        else:
            price_signal = "Low price sensitivity — maintain pricing"
            confidence = 0.68
            recommendation = "Healthy conversion — no urgent markdown needed"

        reasoning = (
            f"Cart abandonment rate: {abandonment:.1f}%. "
            f"Total tracked sessions: {total_sessions:,}. "
            f"Signal: {price_signal}. "
            f"Behavioral analytics suggest customers are "
            f"{'highly' if abandonment > 70 else 'moderately'} price-sensitive."
        )

        return AgentOutput(
            agent_name=self.name,
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning,
            data={
                "cart_abandonment_rate": round(abandonment, 1),
                "price_signal": price_signal,
                "total_sessions": total_sessions
            }
        )


class CoordinatorAgent:
    name = "Coordinator Agent"
    icon = "🧠"

    def coordinate(
        self,
        product: pd.Series,
        pricing_out: AgentOutput,
        inventory_out: AgentOutput,
        demand_out: AgentOutput,
        promotion_out: AgentOutput,
        behavior_out: AgentOutput,
    ) -> Dict[str, Any]:
        # Weighted consensus
        markdown = pricing_out.data.get("recommended_markdown", 10)
        clearance_prob = promotion_out.data.get("clearance_probability", 50)
        revenue_uplift = promotion_out.data.get("revenue_uplift_pct", 0)
        margin_impact = promotion_out.data.get("margin_impact", -5)

        # Risk level
        urgency = inventory_out.data.get("urgency", "LOW")
        risk_map = {"CRITICAL": "🔴 Critical", "HIGH": "🟠 High", "MEDIUM": "🟡 Medium", "LOW": "🟢 Low"}
        risk_level = risk_map.get(urgency, "🟢 Low")

        # Confidence weighted average
        agents = [pricing_out, inventory_out, demand_out, promotion_out, behavior_out]
        avg_confidence = np.mean([a.confidence for a in agents])

        final_reasoning = (
            f"**Coordinator Synthesis:** After analyzing inputs from all 5 specialized agents:\n\n"
            f"- **Pricing Agent** recommends {markdown:.1f}% markdown based on elasticity and margin analysis\n"
            f"- **Inventory Agent** flags {urgency} urgency with {inventory_out.data.get('days_of_stock', 'N/A'):.0f} days of stock\n"
            f"- **Demand Agent** forecasts {demand_out.data.get('forecast_30d', 0):.0f} units in 30 days ({demand_out.data.get('demand_outlook')})\n"
            f"- **Promotion Agent** estimates {revenue_uplift:.1f}% revenue uplift via {promotion_out.data.get('strategy')}\n"
            f"- **Behavior Agent** detects {behavior_out.data.get('cart_abandonment_rate', 0):.1f}% cart abandonment rate\n\n"
            f"**Final Decision:** Apply {markdown:.1f}% markdown with {promotion_out.data.get('strategy', 'standard')} strategy. "
            f"Expected clearance probability: {clearance_prob:.0f}%."
        )

        return {
            "recommended_markdown": round(markdown, 1),
            "risk_level": risk_level,
            "revenue_uplift_pct": round(revenue_uplift, 1),
            "margin_impact": round(margin_impact, 1),
            "clearance_probability": round(clearance_prob, 1),
            "confidence": round(avg_confidence * 100, 0),
            "strategy": promotion_out.data.get("strategy", "Standard Promotion"),
            "reasoning": final_reasoning,
            "agent_outputs": {a.agent_name: a for a in agents}
        }


class RetailAISystem:
    def __init__(self):
        self.pricing_agent = PricingAgent()
        self.inventory_agent = InventoryAgent()
        self.demand_agent = DemandForecastingAgent()
        self.promotion_agent = PromotionAgent()
        self.behavior_agent = CustomerBehaviorAgent()
        self.coordinator = CoordinatorAgent()

    def run(self, product: pd.Series, event_metrics: Dict, elasticity: float = -1.2) -> Dict:
        cart_abandonment = event_metrics.get("cart_abandonment_rate", 60)
        
        pricing_out = self.pricing_agent.analyze(product, elasticity)
        inventory_out = self.inventory_agent.analyze(product)
        demand_out = self.demand_agent.analyze(product)
        markdown = pricing_out.data.get("recommended_markdown", 10)
        promotion_out = self.promotion_agent.analyze(product, markdown, elasticity)
        behavior_out = self.behavior_agent.analyze(cart_abandonment, event_metrics)

        return self.coordinator.coordinate(
            product, pricing_out, inventory_out, demand_out, promotion_out, behavior_out
        )
