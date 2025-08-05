# 🧪 **WhatsApp Agent Testing Guide**

## 📝 **Available Testing Tools**

### **1. Full Automated Test Suite** 📊
**File**: `automated_test_suite.py`
- Tests all 10 common questions automatically
- Validates responses with scoring system
- Generates comprehensive report
- Checks formatting, features, response types

### **2. Quick Test Script** ⚡
**File**: `quick_test.py`  
- Fast testing of specific questions
- Minimal output for rapid iteration
- Test single questions or all at once
- Quick issue detection

### **3. Interactive Test Client** 💬
**File**: `local_test_client.py` (existing)
- Manual testing with conversation flow
- Command-based interface
- Session management
- Real-time interaction

### **4. Test Runner** 🚀
**File**: `run_tests.sh`
- Easy wrapper for all test types
- Simple command-line interface

## 🎯 **The 10 Test Questions**

These questions cover the most common user scenarios:

1. **"i am looking for some properties to buy"** - General property search
2. **"what all apartments do u have"** - Apartment-specific search  
3. **"show me some villas or apartments to rent"** - Multi-type rental search
4. **"what is the cheapest property to buy"** - Statistical/price query
5. **"which property have the most easy amenities"** - Amenity-based search
6. **"which property have a burj khalifa view"** - Location/view-specific search
7. **"i am looking for a quiet neighborhood to rent property can u show some"** - Neighborhood-based search
8. **"can u share some market insights of the property u have"** - Market insights request
9. **"how can i schedule visit bro?"** - Visit scheduling query
10. **"what is the most premium property u have and why?"** - Premium property search

## 🚀 **How to Run Tests**

### **Easy Way (Test Runner)**:
```bash
# Full comprehensive testing
./run_tests.sh full

# Quick test all questions
./run_tests.sh quick

# Quick test specific question
./run_tests.sh quick 5

# Interactive testing
./run_tests.sh interactive
```

### **Direct Python Execution**:
```bash
# Full automated suite
python3 automated_test_suite.py

# Quick tests
python3 quick_test.py all           # All questions
python3 quick_test.py 3             # Question 3 only
python3 quick_test.py "custom query" # Custom question

# Interactive client
python3 local_test_client.py
```

## 📊 **Test Validation Criteria**

Each response is scored out of 10 points:

### **Response Length (2 points)**
- Minimum length requirements met
- Not too short or empty

### **Expected Features (4 points)**
- Contains relevant keywords for the query type
- Includes expected response elements

### **WhatsApp Formatting (2 points)**
- Uses correct `*bold*` instead of `**bold**`
- Includes appropriate emojis

### **No Technical Jargon (1 point)**
- No "ref:", "id:", "error:" visible to user
- Clean user-friendly language

### **Appropriate Response Type (1 point)**
- Property search queries return property results
- Conversation queries get conversational responses
- Statistical queries get statistical answers

### **Pass Threshold**: 7/10 (70%)

## 🔧 **Expected Results After Fixes**

### **For 7+ Properties Found**:
- ✅ Carousel automatically sent
- ✅ Simple text response: "🏠 Here are X properties! I've sent you property cards with all the details."
- ✅ No long property lists in text

### **For <7 Properties Found**:
- ✅ Clean WhatsApp-formatted list
- ✅ Correct `*bold*` formatting
- ✅ No ref IDs or technical jargon
- ✅ Emojis and proper structure

### **For All Responses**:
- ✅ Fast response times (<2s)
- ✅ Mobile-friendly formatting
- ✅ Casual but professional tone
- ✅ Clear next steps for users

## 📈 **Using Test Results**

### **Green (Passing) Results**:
- Agent working as expected
- Ready for production use
- Performance meeting targets

### **Yellow (Some Issues)**:
- Minor formatting problems
- Occasional missing features
- Fine-tuning needed

### **Red (Failing) Results**:
- Major functionality broken
- Wrong response types
- Formatting severely off
- Requires immediate fixes

## 🔄 **Development Workflow**

1. **Make changes** to agent code
2. **Run quick test** for rapid feedback:
   ```bash
   ./run_tests.sh quick
   ```
3. **Fix any issues** identified
4. **Run full test suite** before deploying:
   ```bash
   ./run_tests.sh full
   ```
5. **Check pass rate** is >80% for production

## 📝 **Editing Test Questions**

To modify the test questions, edit the `test_questions` array in:
- `automated_test_suite.py` (lines 40-100)
- `quick_test.py` (lines 20-35)

You can:
- ✅ Change question text
- ✅ Add new questions
- ✅ Modify expected features
- ✅ Adjust validation criteria

## 🎯 **Next Steps**

1. **Run initial tests** to see current performance
2. **Identify common issues** from test results
3. **Fix highest-impact problems** first
4. **Re-test** to validate fixes
5. **Iterate** until >90% pass rate

**Happy testing!** 🚀📱