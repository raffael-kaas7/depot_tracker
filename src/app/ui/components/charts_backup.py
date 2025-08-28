"""
Allocation charts component for Depot Tracker.

This module provides pie chart visualizations for portfolio allocation analysis
based on the comprehensive WKN metadata. It creates interactive pie charts for
asset class, sector, region, and risk estimation breakdowns.
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Optional


def create_allocation_pie_chart(df: pd.DataFrame, category: str, title: str) -> go.Figure:
    """
    Create a pie chart for allocation analysis using dynamic allocation columns.
    
    This function works with the enhanced allocation columns that distribute ETF
    values across multiple regions/sectors based on their breakdown percentages.
    
    Args:
        df: DataFrame with position data including dynamic allocation columns
        category: Category type ('region' or 'sector')
        title: Title for the chart
        
    Returns:
        Plotly figure object for the pie chart
    """
    if df is None or df.empty:
        return _create_empty_chart(title, "No data available")
    
    # Get allocation data by summing the relevant allocation columns
    allocation_data = _get_allocation_data(df, category)
    
    if allocation_data.empty or allocation_data['value'].sum() == 0:
        return _create_empty_chart(title, f"No {category} allocation data available")
    
    # Filter out zero values
    allocation_data = allocation_data[allocation_data['value'] > 0]
    
    if allocation_data.empty:
        return _create_empty_chart(title, f"No {category} allocation data available")
    
    # Calculate percentages
    total_value = allocation_data['value'].sum()
    allocation_data['percentage'] = (allocation_data['value'] / total_value * 100).round(1)
    
    # Sort by value for better visualization
    allocation_data = allocation_data.sort_values('value', ascending=False)
    
    # Create pie chart with custom colors
    color_schemes = {
        'asset_class': px.colors.qualitative.Set3,
        'sector': px.colors.qualitative.Pastel,
        'region': px.colors.qualitative.Set2,
        'risk_estimation': ['#2E8B57', '#FFD700', '#DC143C']  # Green, Yellow, Red
    }
    
    colors = color_schemes.get(category, px.colors.qualitative.Set1)
    
    
    fig = go.Figure(data=[go.Pie(
        labels=allocation_data['category'],
        values=allocation_data['value'],
        textinfo='label+percent',
        textposition='outside',
        textfont_size=12,
        marker=dict(
            colors=colors[:len(allocation_data)],
            line=dict(color='#000000', width=2)
        ),
        hovertemplate='<b>%{label}</b><br>' +
                     'Value: €%{value:,.0f}<br>' +
                     'Percentage: %{percent}<br>' +
                     '<extra></extra>'
    )])
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': 'white'}
        },
        font=dict(color='white'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05,
            font=dict(color='white')
        )
    )
    
    return fig


def _create_empty_chart(title: str, message: str) -> go.Figure:
    """Create an empty chart with a message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font_size=16
    )
    fig.update_layout(
        title=title,
        showlegend=False,
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig


def _get_allocation_data(df: pd.DataFrame, category: str) -> pd.DataFrame:
    """
    Extract allocation data by summing the relevant dynamic allocation columns.
    
    Args:
        df: DataFrame with allocation columns
        category: 'region' or 'sector'
        
    Returns:
        DataFrame with category and value columns
    """
    # Find all columns that match the category pattern
    pattern = f"{category}_"
    allocation_columns = [col for col in df.columns if col.startswith(pattern) and col.endswith("_value")]
    
    if not allocation_columns:
        return pd.DataFrame(columns=['category', 'value'])
    
    # Sum values for each allocation column
    results = []
    for col in allocation_columns:
        total_value = df[col].sum()
        if total_value > 0:  # Only include non-zero allocations
            # Extract category name from column name
            category_name = col.replace(f"{category}_", "").replace("_value", "").replace("_", " ").title()
            results.append({
                'category': category_name,
                'value': total_value
            })
    
    return pd.DataFrame(results)


def _get_non_zero_positions(df: pd.DataFrame, category: str) -> pd.DataFrame:
    """Get positions that have non-zero allocation for the given category."""
    pattern = f"{category}_"
    allocation_columns = [col for col in df.columns if col.startswith(pattern) and col.endswith("_value")]
    
    if not allocation_columns:
        return pd.DataFrame()
    
    # Find rows where at least one allocation column is non-zero
    mask = df[allocation_columns].sum(axis=1) > 0
    return df[mask]
    
    # Check if category column exists
    if category not in filtered_df.columns:
        filtered_df[category] = "Unknown"
    
    # Filter out empty, None, or placeholder values
    excluded_values = ["", "Unknown", None, "N/A", "n/a"]
    filtered_df = filtered_df[~filtered_df[category].isin(excluded_values)]
    
    # Also filter out NaN values
    filtered_df = filtered_df.dropna(subset=[category])
    
    # Remove whitespace-only values
    filtered_df = filtered_df[filtered_df[category].str.strip() != ""]
    
    if filtered_df.empty:
        # Create chart with message about filtered data
        fig = go.Figure()
        total_excluded = len(df) - len(filtered_df)
        fig.add_annotation(
            text=f"No valid {category.replace('_', ' ')} data<br>({total_excluded} assets excluded)",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font_size=16
        )
        fig.update_layout(
            title=title,
            showlegend=False,
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    
    # Group by category and sum current values
    allocation_data = filtered_df.groupby(category)['current_value'].sum().reset_index()
    allocation_data = allocation_data[allocation_data['current_value'] > 0]  # Remove zero values
    
    if allocation_data.empty:
        # Create empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="No allocation data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font_size=16
        )
        fig.update_layout(
            title=title,
            showlegend=False,
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    
    # Calculate percentages
    total_value = allocation_data['current_value'].sum()
    allocation_data['percentage'] = (allocation_data['current_value'] / total_value * 100).round(1)
    
    # Calculate excluded assets for informational purposes
    total_assets = len(df)
    included_assets = len(filtered_df)
    excluded_assets = total_assets - included_assets
    
    # Update title to include exclusion information if any assets were filtered
    display_title = title
    if excluded_assets > 0:
        display_title += f" ({excluded_assets} assets excluded)"
    
    # Create pie chart with custom colors based on category
    color_schemes = {
        'asset_class': px.colors.qualitative.Set3,
        'sector': px.colors.qualitative.Pastel,
        'region': px.colors.qualitative.Set2,
        'risk_estimation': ['#2E8B57', '#FFD700', '#DC143C']  # Green, Yellow, Red for Low, Medium, High
    }
    
    colors = color_schemes.get(category, px.colors.qualitative.Set1)
    
    fig = go.Figure(data=[go.Pie(
        labels=allocation_data[category],
        values=allocation_data['current_value'],
        textinfo='label+percent',
        textposition='outside',
        textfont_size=12,
        marker=dict(
            colors=colors[:len(allocation_data)],
            line=dict(color='#000000', width=2)
        ),
        hovertemplate='<b>%{label}</b><br>' +
                     'Value: €%{value:,.0f}<br>' +
                     'Percentage: %{percent}<br>' +
                     '<extra></extra>'
    )])
    
    fig.update_layout(
        title={
            'text': display_title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': 'white'}
        },
        font=dict(color='white'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05,
            font=dict(color='white')
        )
    )
    
    return fig