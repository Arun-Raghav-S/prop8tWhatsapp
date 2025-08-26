# WhatsApp Agent Flow Emulator 🧪

This test suite emulates the exact conversation flow from your extracted_payloads.log to test the entire WhatsApp Agent system end-to-end.

## 🎯 What This Tests

- **Complete Message Flow**: From initial greeting to property search to button interactions
- **Button Handling**: "Know More" and "Schedule Visit" buttons with real property IDs
- **AI Response Generation**: Full conversation management and tool usage
- **Log Generation**: Verification that events are properly logged
- **Real Phone Integration**: Uses your actual business account and phone number

## 📋 Setup

1. **Make sure your processing worker is running:**
   ```bash
   # In the main processing-worker directory
   python main.py
   ```

2. **Install test dependencies:**
   ```bash
   cd tests/flow_emulator
   pip install -r requirements.txt
   ```

## 🚀 Running Tests

### Quick Test (Basic Property Search)
```bash
python run_test.py quick
```
This tests:
- Initial greeting → AI asks for requirements
- Property search request → AI asks buy/rent
- "Buy" response → AI searches and sends property carousel

### Button Test (Know More & Schedule Visit)
```bash
python run_test.py buttons
```
This tests:
- Property search setup
- "Know More" button click → Property details
- "Schedule Visit" button click → Scheduling flow
- Date/time input → Visit confirmation

### Full Journey Test (Complete Flow)
```bash
python run_test.py full
```
This runs the exact sequence from your logs:
1. "Hi"
2. "Show me some apartments anywhere and any price bro"  
3. "Buy"
4. Know More button (property: 4900fde3-eaf4-4bf5-ab3f-241248f512e5)
5. Schedule Visit button (property: a839d7a9-4035-4c3f-accd-b71286ee0aad)
6. "Tomorrow at 3 PM"

### Custom Flow Test
```bash
python run_test.py flow <flow_name>
```
Available flows:
- `basic_property_search`
- `rental_search` 
- `button_interaction`
- `full_journey`

## 📱 What You'll See

### 1. In Your WhatsApp
You should receive messages on **+918281840462** from the AI agent with:
- Welcome messages asking for requirements
- Property carousels with "Know More" and "Schedule Visit" buttons
- Property details when clicking "Know More"
- Scheduling prompts when clicking "Schedule Visit"

### 2. In extracted_payloads.log
New entries will be added showing:
```
📥 RECEIVED_ENVELOPE: {}
💬 MESSAGE_RECEIVED: from=None, type=whatsapp_business_account
🔍 RAW_AISENSY_MESSAGE: {...}
🔘 BUTTON_CLICK: 'Know More' from +918281840462
```

### 3. In Console Output
The test script shows:
```
🚀 SENDING MESSAGE #1
📱 From: +918281840462
💬 Text: 'Hi'
🔧 Business Account: 543107385407043
✅ Response Status: 200
⏳ Waiting 5 seconds for processing...
```

## 🔧 Configuration

The tests use the exact same data from your logs:

- **Business Account**: `543107385407043`
- **Phone Number**: `+918281840462`
- **Property IDs**: Real IDs from your carousel (for button testing)
- **Server URL**: `http://localhost:8080` (configurable)

You can modify these in `config.py` if needed.

## 🐛 Troubleshooting

### "Cannot reach server"
```bash
# Check if processing worker is running
curl http://localhost:8080/
```

### "No valid access token"
- Make sure your environment variables are set correctly
- Check if tokens are cached properly in the system

### "Property not found" 
- The property IDs in the test are from your actual logs
- If properties were deleted, you can update the IDs in `config.py`

### "Button clicks not working"
- This means our recent fixes worked! 
- Check the console output for specific error messages

## 📊 Monitoring Logs

To watch logs in real-time while testing:

```bash
# In another terminal
tail -f logs/extracted_payloads.log
```

## 🎬 Test Sequence Details

The full test emulates this exact conversation:

1. **User**: "Hi"
   - **Expected**: AI greeting asking for requirements

2. **User**: "Show me some apartments anywhere and any price bro"
   - **Expected**: AI asks if buying or renting

3. **User**: "Buy"
   - **Expected**: AI searches properties, sends carousel with 10 properties

4. **User**: Clicks "Know More" on property `4900fde3-eaf4-4bf5-ab3f-241248f512e5`
   - **Expected**: Property details (beds, baths, price, location, features)

5. **User**: Clicks "Schedule Visit" on property `a839d7a9-4035-4c3f-accd-b71286ee0aad`
   - **Expected**: Scheduling prompt asking for date/time

6. **User**: "Tomorrow at 3 PM"
   - **Expected**: Visit confirmation with details

## ✅ Success Indicators

✅ **All HTTP responses return 200 status**
✅ **You receive WhatsApp messages on +918281840462**
✅ **Property carousel appears with clickable buttons**
✅ **"Know More" shows property details**
✅ **"Schedule Visit" starts scheduling flow**
✅ **New entries appear in extracted_payloads.log**
✅ **No error messages in server console**

If all these work, your button handling and AI flow are perfect! 🎉
