# Twitter Sentiment Analysis System

A comprehensive Python system for analyzing Twitter sentiment with price correlation analysis and automated daily reporting.

## Features

- **Sentiment Analysis**: Analyzes daily tweets from followed accounts using VADER and TextBlob
- **Price Correlation**: Correlates sentiment with oil prices (WTI/Brent) and German electricity prices
- **Data Storage**: Stores results in InfluxDB with historical tracking
- **Daily Reports**: Automated email reports with visualizations and insights
- **Trend Analysis**: Identifies sentiment shifts and trending topics

## Setup

### Prerequisites

- Python 3.8+
- InfluxDB instance
- SMTP email server access
- Nitter instance (optional, for enhanced scraping)

### Installation

1. Clone or download the project files
2. Run the setup script:
   ```bash
   python setup.py
   ```

3. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your actual configuration
   ```

4. Update the followed accounts list:
   ```bash
   # Edit followed_accounts.txt with Twitter handles to monitor
   ```

### Configuration

Edit the `.env` file with your settings:

```env
# Nitter VM Configuration (optional)
NITTER_BASE_URL=https://your-nitter-instance.com
NITTER_USERNAME=your_username
NITTER_PASSWORD=your_password

# InfluxDB Configuration (required)
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=your_organization
INFLUXDB_BUCKET=your_bucket_name

# Email Configuration (required)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
RECIPIENT_EMAIL=recipient@example.com

# Analysis Configuration
REPORT_TIME=08:00
TIMEZONE=UTC
DAYS_HISTORY=30
MIN_TWEETS_FOR_ANALYSIS=5
```

## Usage

### Run Analysis Once
```bash
python main.py --run-now
```

### Start Scheduled Analysis
```bash
python main.py
```

The system will run daily at the configured time and send email reports.

## System Components

### Core Modules

- **`main.py`**: Main orchestrator and scheduler
- **`config.py`**: Configuration management
- **`nitter_client.py`**: Twitter data scraping via Nitter
- **`sentiment_analyzer.py`**: Sentiment analysis using VADER and TextBlob
- **`influxdb_client.py`**: InfluxDB data storage and retrieval
- **`correlation_analyzer.py`**: Price correlation analysis
- **`report_generator.py`**: HTML report generation and email sending
- **`logger.py`**: Logging configuration

### Data Flow

1. **Data Collection**: Scrape tweets from followed accounts
2. **Sentiment Analysis**: Analyze tweet sentiment using multiple algorithms
3. **Data Storage**: Store results in InfluxDB with timestamps
4. **Correlation Analysis**: Calculate correlations with price data
5. **Report Generation**: Create HTML reports with visualizations
6. **Email Delivery**: Send reports to configured recipients

## Report Contents

Daily reports include:

- **Top 5 Positive/Negative Sentiment Accounts**
- **Notable Sentiment Shifts** from previous periods
- **Price Correlation Analysis** (oil and electricity)
- **Trending Topics** from analyzed tweets
- **Data Visualizations** (charts and graphs)

## Price Data Requirements

The system expects price data in InfluxDB with these measurements:

### Oil Prices
- Measurement: `oil_prices`
- Fields: `wti_price`, `brent_price`

### Electricity Prices
- Measurement: `electricity_prices`
- Fields: `german_price`

## Keywords for Correlation

### Oil-related Keywords
- WTI, Brent, crude oil, OPEC, oil price, petroleum, barrel

### Electricity-related Keywords
- Strompreis, Energiekosten, kWh, electricity price, power price, energy cost

## Error Handling

The system includes comprehensive error handling:

- **Logging**: All activities logged to file and console
- **Graceful Failures**: Individual account failures don't stop the entire analysis
- **Error Notifications**: Email alerts for system errors
- **Data Validation**: Checks for minimum data requirements

## Monitoring

Monitor the system through:

- **Log Files**: Check `sentiment_analysis.log` for detailed logs
- **InfluxDB**: Query stored data for system health
- **Email Reports**: Daily reports indicate system status

## Customization

### Adding New Accounts
Edit `followed_accounts.txt` and add Twitter handles (one per line).

### Modifying Analysis Parameters
Update configuration in `.env` file:
- `MIN_TWEETS_FOR_ANALYSIS`: Minimum tweets required for analysis
- `DAYS_HISTORY`: Historical data period for correlation analysis
- `REPORT_TIME`: Daily report delivery time

### Custom Keywords
Modify keyword lists in `config.py`:
- `OIL_KEYWORDS`: Keywords for oil-related tweet detection
- `ELECTRICITY_KEYWORDS`: Keywords for electricity-related tweet detection

## Troubleshooting

### Common Issues

1. **No tweets found**: Check if accounts are public and handles are correct
2. **InfluxDB connection errors**: Verify database credentials and connectivity
3. **Email delivery failures**: Check SMTP settings and authentication
4. **Rate limiting**: System includes delays to avoid rate limits

### Debug Mode
Run with immediate execution to test:
```bash
python main.py --run-now
```

## Security Considerations

- Store sensitive credentials in `.env` file (not in version control)
- Use app-specific passwords for email authentication
- Secure your InfluxDB instance with proper authentication
- Consider using environment variables in production

## Performance

- **Rate Limiting**: Built-in delays to respect API limits
- **Batch Processing**: Efficient analysis of multiple accounts
- **Data Aggregation**: Daily summaries reduce storage requirements
- **Error Recovery**: Continues processing despite individual failures

## License

This project is provided as-is for educational and research purposes.

## Support

For issues and questions:
1. Check the log files for detailed error information
2. Verify configuration settings in `.env`
3. Ensure all required services (InfluxDB, SMTP) are accessible
4. Test individual components with the `--run-now` flag