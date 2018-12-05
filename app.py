from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

# endpoint to get user detail by id
@app.route("/quiz/<income>/<citizen>/<expenditure>/<first_choice>/<second_choice>/<third_choice>", methods=["GET"])
def user_detail(income, citizen, expenditure, first_choice, second_choice, third_choice):
    input_data = {"income": int(str(income)) * 12, # Check if eligible
              "citizen": str(citizen), 
              "expenditure": int(str(expenditure)),# fee.annual should be less than 1% of expenditure
              "first_choice" : str(first_choice),
              "second_choice" : str(second_choice),
              "third_choice" : str(third_choice)}
    df = apply_filter(input_data)
    json_df = df.to_json(orient='split')
    return json_df

import pandas as pd
import ast
from re import finditer

def apply_filter(input_data):
    df = pd.read_csv("credit_card_scores.csv")
    print(df.columns)
    
    # filter by eligibility
    if input_data['citizen'] == "Singaporean":
        income_limit = 'income.singapore_conv'
    else:
        income_limit = 'income.foreign_conv'
    df_1_filtered = df[df[income_limit] <= input_data['income']]
    # filter by expenditure
    #df_2_filtered = df_1_filtered[df_1_filtered['fee.annual_conv'] * 100 <= input_data['expenditure']]
    df_2_filtered = df_1_filtered
    # Initialize final results
    df_3_filtered = pd.DataFrame()
    
    list_of_preferences = ["preferences.petrol", # Map to petrol
                           "preferences.dining", # Map to dining
                           "preferences.grocery", # Map to groceries
                           "preferences.shopping", # Map to shopping
                           "preferences.onlineshopping", # Map to online shopping
                           "preferences.entertainment", # Map to cashback
                           "preferences.travel", # Map to airmiles
                           "preferences.utilities", # Ignore
                           "preferences.beauty", # Map to cashback
                           "preferences.debt_servicing" # Map to interest rate
                          ]
    
    preference_dict ={}
    # First choice given 0.35 weight
    # Second choice given 0.25 weight
    # Third choice given 0.15 weight
    # The rest given 0.025 weight
    preference_dict[input_data['first_choice']] = 0.35
    preference_dict[input_data['second_choice']] = 0.25
    preference_dict[input_data['third_choice']] = 0.15
    for preference in list_of_preferences:
        if preference not in input_data.values():
            preference_dict[preference] = 0.025

    # Apply weights to scoring matrix
    df_3_filtered["preferences.petrol"] = preference_dict["preferences.petrol"] * df_2_filtered["benefits.petrol.score"]
    df_3_filtered["preferences.dining"] = preference_dict["preferences.dining"] * df_2_filtered["benefits.dining.score"]
    df_3_filtered["preferences.grocery"] = preference_dict["preferences.grocery"] * df_2_filtered["benefits.grocery.score"]
    df_3_filtered["preferences.shopping"] = preference_dict["preferences.shopping"] * df_2_filtered["Shopping.score"]
    df_3_filtered["preferences.onlineshopping"] = preference_dict["preferences.onlineshopping"] * df_2_filtered["benefits.onlineshop.score"]
    df_3_filtered["preferences.entertainment"] = preference_dict["preferences.entertainment"] * df_2_filtered["benefits.cashback.score"]
    df_3_filtered["preferences.travel"] = preference_dict["preferences.travel"] * df_2_filtered["benefits.airmile.score"]
    df_3_filtered["preferences.beauty"] = preference_dict["preferences.beauty"] * df_2_filtered["benefits.cashback.score"]
    df_3_filtered["preferences.debt_servicing"] = preference_dict["preferences.debt_servicing"] * df_2_filtered["interest.rate_conv"]
    df_3_filtered["Final Score"] = df_3_filtered.sum(axis = 1)
    df_3_filtered['card'] = df_2_filtered['card']
    list_of_benefits = ['benefits.airmile',
       'benefits.cashback', 'benefits.dining', 'benefits.grocery',
       'benefits.onlineshop', 'benefits.petrol', 'Rewards', 'Shopping',
       'Student']
    for i in list_of_benefits:
        df_3_filtered[i] = df_2_filtered[i].fillna(0)
    df_3_filtered.sort_values(by=["Final Score"], inplace = True, ascending = False)
    df_3_filtered.reset_index(inplace = True)
    result = df_3_filtered.head(3)[['card', 'Final Score', 'benefits.airmile',
       'benefits.cashback', 'benefits.dining', 'benefits.grocery',
       'benefits.onlineshop', 'benefits.petrol', 'Rewards', 'Shopping',
       'Student']]
    
    cardlinks = {"american" : ['https://www.americanexpress.com/sg/credit-cards/all-cards/'],
    "bank-of-china" : ['http://www.bankofchina.com/sg/bcservice/bc1/'], # need to do further validation for the card type
    "maybank" : ['https://apply.maybank.com.sg/cards/#/creditcardstart?sc=acq4'],
    "cimb" : ['https://www.cimbbank.com.sg/en/personal/products/cards/credit-cards.html'], # need to have .html
    "posb" : ['https://www.posb.com.sg/personal/cards/credit-cards/posb-everyday-card'],
    "dbs" : ['https://www.dbs.com.sg/personal/cards/credit-cards/'],
    "uob" : ['https://www.uob.com.sg/credit-cards/all-cards.html?ms=pweb-cards-home'], #that's it, don't need to do anything else
    "hsbc" : ['https://www.hsbc.com.sg/1/2/personal/cards/'],
    "ocbc" : ['https://www.ocbc.com/personal-banking/cards/'], # may need to either !) strip the -, 2) associate with the payment merchant, 3) or do both
    "ocbc-frank" : ['http://www.frankbyocbc.com/products/cards/credit-card/'],
    "citi" : ['https://www.citibank.com.sg/gcb/credit_cards/credit-card.htm'],
    "standard" : ['https://www.sc.com/sg/credit-cards/']} # need to change the name accordingly
        
    def get_link(card):
        for i in cardlinks.keys():
            if i in card:
                return cardlinks[i][0]
            
    def clean_up(card):
        cards_split = card.split('-')
        cards_split = [card.upper() for card in cards_split]
        result = ' '.join(cards_split) 
        return result
        
    result['card-link'] = result['card'].apply(get_link)
    result['full-name'] = result['card'].apply(clean_up)

    for i in list_of_benefits:
        result[i] = result[i].apply(lambda x : ast.literal_eval(x))
        
    def camel_case_split(identifier):
        matches = finditer('.+?(?:(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
        return [m.group(0) for m in matches]
        
    def compile_string(row):
        counter = 1
        result = ""
        for i in list_of_benefits:
            if row[i] != 0:
                for value in row[i]:
                    value = value.replace("X", "x")
                    value = camel_case_split(value)
                    for item in value:
                        result += str(counter) + ". " + item + "\n" + "\n"
                        counter += 1
        print(result)
        return result

    result["benefits.keyfeatures"] = result.apply(compile_string, axis = 1)
    result = result[["card","Final Score","benefits.keyfeatures","card-link","full-name"]]
    return result

if __name__ == '__main__':
    app.run(debug=True)