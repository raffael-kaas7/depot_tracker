"""
Allocation charts component for Depot Tracker.

This module provides pie chart visualizations for portfolio allocation analysis
using dynamic allocation columns that handle ETF breakdowns. It creates 
interactive pie charts for asset class, sector, region, and risk estimation.
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
        category: Category type ('region', 'sector', 'asset_class', 'risk_estimation')
        title: Title for the chart
        
    Returns:
        Plotly figure object for the pie chart
    """
    if df is None or df.empty:
        return _create_empty_chart(title, "No data available")
    
    # Handle allocation based on category type
    if category in ['region', 'sector']:
        # Use dynamic allocation columns for region and sector
        allocation_data = _get_allocation_data(df, category)
    else:
        # Use traditional grouping for asset_class and risk_estimation
        allocation_data = _get_traditional_allocation_data(df, category)
    
    if allocation_data.empty or allocation_data['value'].sum() == 0:
        return _create_empty_chart(title, f"No {category.replace('_', ' ')} allocation data available")
    
    # Filter out zero values
    allocation_data = allocation_data[allocation_data['value'] > 0]
    
    if allocation_data.empty:
        return _create_empty_chart(title, f"No {category.replace('_', ' ')} allocation data available")
    
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
        'risk_estimation': ['#2E8B57', '#DC143C', '#FFD700']  # Green, Yellow, Red
    }
    
    colors = color_schemes.get(category, px.colors.qualitative.Set1)
    
    # Configure text display - use clean approach with no labels on slices
    # All information available in legend and on hover for cleaner visualization
    textinfo = 'none'  # Only show in legend and on hover
    textposition = 'inside'
    
    fig = go.Figure(data=[go.Pie(
        labels=allocation_data['category'],
        values=allocation_data['value'],
        textinfo=textinfo,
        textposition=textposition,
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


def _get_traditional_allocation_data(df: pd.DataFrame, category: str) -> pd.DataFrame:
    """
    Extract allocation data using traditional grouping for non-dynamic categories.
    
    Args:
        df: DataFrame with position data
        category: 'asset_class' or 'risk_estimation'
        
    Returns:
        DataFrame with category and value columns
    """
    if category not in df.columns:
        return pd.DataFrame(columns=['category', 'value'])
    
    # Filter out empty/unknown values
    filtered_df = df[df[category].notna() & (df[category] != "") & (df[category] != "Unknown")]
    
    if filtered_df.empty:
        return pd.DataFrame(columns=['category', 'value'])
    
    # Group and sum
    result = filtered_df.groupby(category)['current_value'].sum().reset_index()
    result = result[result['current_value'] > 0]
    result.rename(columns={category: 'category', 'current_value': 'value'}, inplace=True)
    
    return result


def _get_non_zero_positions(df: pd.DataFrame, category: str) -> pd.DataFrame:
    """Get positions that have non-zero allocation for the given category."""
    pattern = f"{category}_"
    allocation_columns = [col for col in df.columns if col.startswith(pattern) and col.endswith("_value")]
    
    if not allocation_columns:
        return pd.DataFrame()
    
    # Find rows where at least one allocation column is non-zero
    mask = df[allocation_columns].sum(axis=1) > 0
    return df[mask]


def create_allocation_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a summary table showing allocation breakdown across all categories.
    
    This function uses the dynamic allocation columns to provide comprehensive
    allocation analysis including ETF breakdown distributions.
    
    Args:
        df: DataFrame with position data including dynamic allocation columns
        
    Returns:
        DataFrame with allocation summary across all categories
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    summaries = []
    
    # Handle dynamic allocation categories (region, sector)
    for category in ['region', 'sector']:
        category_data = _get_allocation_data(df, category)
        if not category_data.empty:
            category_data['category_type'] = category.replace('_', ' ').title()
            category_data.rename(columns={'category': 'category_value', 'value': 'current_value'}, inplace=True)
            summaries.append(category_data)
    
    # Handle traditional categories (asset_class, risk_estimation)
    for category in ['asset_class', 'risk_estimation']:
        category_data = _get_traditional_allocation_data(df, category)
        if not category_data.empty:
            category_data['category_type'] = category.replace('_', ' ').title()
            category_data.rename(columns={'category': 'category_value', 'value': 'current_value'}, inplace=True)
            summaries.append(category_data)
    
    # Combine all summaries
    if summaries:
        summary_df = pd.concat(summaries, ignore_index=True)
        
        # Calculate percentages
        total_value = df['current_value'].sum()
        summary_df['percentage'] = (summary_df['current_value'] / total_value * 100).round(1)
        
        # Reorder columns and sort
        summary_df = summary_df[['category_type', 'category_value', 'current_value', 'percentage']]
        summary_df.columns = ['Category Type', 'Category', 'Value (€)', 'Percentage (%)']
        return summary_df.sort_values(['Category Type', 'Percentage (%)'], ascending=[True, False])
    
    return pd.DataFrame()


def create_historical_depot_chart(snapshots_data: dict, title: str = "Historical Depot Performance", show_invested_capital: bool = True) -> go.Figure:
    """
    Create a line chart showing historical performance of depot pools over time.
    
    Args:
        snapshots_data: Dictionary with depot names as keys and snapshot data as values
        title: Title for the chart
        show_invested_capital: Whether to show invested capital lines (default: True)
        
    Returns:
        Plotly figure object for the line chart
    """
    if not snapshots_data or all(not data for data in snapshots_data.values()):
        return _create_empty_chart(title, "No historical data available")
    
    fig = go.Figure()
    
    # Color palette for different depots
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for i, (depot_name, snapshots) in enumerate(snapshots_data.items()):
        if not snapshots:
            continue
            
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(snapshots)
        
        if df.empty:
            continue
            
        # Convert date strings to datetime objects
        df['date'] = pd.to_datetime(df['date'])
        
        # Sort by date to ensure proper line connection
        df = df.sort_values('date')
        
        # Calculate performance metrics
        df['profit_loss'] = df['current_value'] - df['invested_capital']
        df['performance_pct'] = ((df['current_value'] - df['invested_capital']) / df['invested_capital'] * 100).round(2)
        
        color = colors[i % len(colors)]
        
        # Add current value line
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['current_value'],
            mode='lines+markers',
            name='Current Value',
            line=dict(color=color, width=2),
            marker=dict(size=4),
            hovertemplate=(
                f'<b>{depot_name}</b><br>' +
                'Date: %{x}<br>' +
                'Current Value: €%{y:,.0f}<br>' +
                'Performance: %{customdata:.1f}%<br>' +
                '<extra></extra>'
            ),
            customdata=df['performance_pct']
        ))
        
        # Add invested capital line (dashed) - always add, but control visibility
        if show_invested_capital:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['invested_capital'],
                mode='lines',
                name='Invested Capital',
                line=dict(color=color, width=1, dash='dash'),
                visible=True,  # Start visible, but can be toggled via legend
                hovertemplate=(
                    f'<b>{depot_name}</b><br>' +
                    'Date: %{x}<br>' +
                    'Invested Capital: €%{y:,.0f}<br>' +
                    '<extra></extra>'
                )
            ))
    
    # Update layout with clickable legend
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': 'white'}
        },
        xaxis_title="Date",
        yaxis_title="Value (€)",
        xaxis=dict(
            gridcolor='rgba(128, 128, 128, 0.2)',
            color='white'
        ),
        yaxis=dict(
            gridcolor='rgba(128, 128, 128, 0.2)',
            color='white',
            tickformat='€,.0f'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0.5)',
            itemclick="toggle",
            itemdoubleclick="toggleothers"
        ),
        hovermode='x unified',
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig


def create_combined_historical_chart(snapshots_data: dict, title: str = "Combined Historical Performance", show_invested_capital: bool = True) -> go.Figure:
    """
    Create a combined line chart showing the sum of all depot values over time.
    
    Args:
        snapshots_data: Dictionary with depot names as keys and snapshot data as values
        title: Title for the chart
        show_invested_capital: Whether to show invested capital line (default: True)
        
    Returns:
        Plotly figure object for the combined line chart
    """
    if not snapshots_data or all(not data for data in snapshots_data.values()):
        return _create_empty_chart(title, "No historical data available")
    
    # Combine all depot data by date
    combined_data = {}
    
    for depot_name, snapshots in snapshots_data.items():
        if not snapshots:
            continue
            
        for snapshot in snapshots:
            date = snapshot['date']
            if date not in combined_data:
                combined_data[date] = {
                    'date': date,
                    'current_value': 0,
                    'invested_capital': 0
                }
            combined_data[date]['current_value'] += snapshot['current_value']
            combined_data[date]['invested_capital'] += snapshot['invested_capital']
    
    if not combined_data:
        return _create_empty_chart(title, "No data to combine")
    
    # Convert to DataFrame
    df = pd.DataFrame(list(combined_data.values()))
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Calculate performance metrics
    df['profit_loss'] = df['current_value'] - df['invested_capital']
    df['performance_pct'] = ((df['current_value'] - df['invested_capital']) / df['invested_capital'] * 100).round(2)
    
    fig = go.Figure()
    
    # Add combined current value line
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['current_value'],
        mode='lines+markers',
        name='Total Current Value',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=5),
        hovertemplate=(
            '<b>Combined Portfolio</b><br>' +
            'Date: %{x}<br>' +
            'Total Value: €%{y:,.0f}<br>' +
            'Performance: %{customdata:.1f}%<br>' +
            '<extra></extra>'
        ),
        customdata=df['performance_pct']
    ))
    
    # Add combined invested capital line (dashed) - always add, but control visibility
    if show_invested_capital:
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['invested_capital'],
            mode='lines',
            name='Total Invested Capital',
            line=dict(color='#1f77b4', width=2, dash='dash'),
            visible=True,  # Start visible, but can be toggled via legend
            hovertemplate=(
                '<b>Combined Portfolio</b><br>' +
                'Date: %{x}<br>' +
                'Invested Capital: €%{y:,.0f}<br>' +
                '<extra></extra>'
            )
        ))
    
    # Update layout with clickable legend
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': 'white'}
        },
        xaxis_title="Date",
        yaxis_title="Value (€)",
        xaxis=dict(
            gridcolor='rgba(128, 128, 128, 0.2)',
            color='white'
        ),
        yaxis=dict(
            gridcolor='rgba(128, 128, 128, 0.2)',
            color='white',
            tickformat='€,.0f'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0.5)',
            # Enable legend clicking to show/hide traces
            itemclick="toggle",
            itemdoubleclick="toggleothers"
        ),
        hovermode='x unified',
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig
