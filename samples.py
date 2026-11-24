"""Example legacy code snippets across supported languages for interactive exploration."""

SAMPLES_BY_LANGUAGE = {
    "Python": {
        "Simple interest": '''def calc_si(p, r, t):
    si = (p * r * t) / 100
    if si < 0:
        si = 0
    return round(si, 2)
''',
        "Account check digit": '''def chk_digit(acc):
    total = 0
    for i, ch in enumerate(reversed(acc)):
        d = int(ch)
        if i % 2 == 0:
            d = d * 2
            if d > 9:
                d = d - 9
        total = total + d
    return (10 - total % 10) % 10
''',
        "Minimum balance penalty": '''def pen(bal, minbal, rate):
    if bal >= minbal:
        return 0
    short = minbal - bal
    fee = short * rate
    if fee < 10:
        fee = 10
    return fee
''',
        "Order processing with discount": '''def process_order(items, discount_rate=0.1, tax_rate=0.05):
    total = 0
    for item in items:
        price = item["price"]
        qty = item["quantity"]
        total += price * qty
    if discount_rate > 0:
        total -= total * discount_rate
    total += total * tax_rate
    return round(total, 2)
'''
    },
    "Java": {
        "Calculate account fee": '''public class AccountManager {
    public static double calculateMaintenanceFee(double balance, int transactions, boolean isPremium) {
        if (isPremium) {
            return 0.0;
        }
        double fee = 5.0;
        if (balance < 1000.0) {
            fee += 10.0;
        }
        if (transactions > 30) {
            fee += (transactions - 30) * 0.25;
        }
        return fee;
    }
}
'''
    },
    "JavaScript": {
        "Cart discount validator": '''function computeCartTotal(cartItems, couponCode, taxPercent) {
    let subtotal = 0;
    for (const item of cartItems) {
        subtotal += item.price * item.quantity;
    }
    let discount = 0;
    if (couponCode === "SAVE20" && subtotal >= 100) {
        discount = subtotal * 0.20;
    }
    const taxedTotal = (subtotal - discount) * (1 + taxPercent / 100);
    return Math.round(taxedTotal * 100) / 100;
}
'''
    },
    "C++": {
        "Interest accrual calculator": '''#include <iostream>
#include <algorithm>

double calculateAccruedInterest(double principal, double annualRate, int months) {
    if (principal <= 0.0 || annualRate <= 0.0 || months <= 0) {
        return 0.0;
    }
    double monthlyRate = annualRate / 12.0;
    double interest = 0.0;
    for (int i = 0; i < months; ++i) {
        double currentGain = (principal + interest) * monthlyRate;
        interest += currentGain;
    }
    return std::max(0.0, interest);
}
'''
    }
}

# Flat dictionary for backward compatibility with existing tests
SAMPLES = SAMPLES_BY_LANGUAGE["Python"]
