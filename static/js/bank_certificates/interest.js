'use strict';

function calculateCertificateInterest() {
    const amount = parseNumberInput('bcAmount') || 0;
    const rate = parseNumberInput('bcInterestRate') || 0; // e.g., 0.10 for 10%
    const frequency = document.getElementById('bcFrequency').value;
    
    // Calculate base yearly interest
    const yearlyInterest = amount * (rate / 100);
    let computedValue = 0;

    if (yearlyInterest <= 0) {
        document.getElementById('bcInterestValue').value = '0.00';
        return;
    }

    switch (frequency) {
        case 'monthly':
            computedValue = yearlyInterest / 12;
            break;
        case 'quarterly':
            computedValue = yearlyInterest / 4;
            break;
        case 'semi_annually':
            computedValue = yearlyInterest / 2;
            break;
        case 'annually':
            computedValue = yearlyInterest;
            break;
        case 'at_maturity':
            const issueDateVal = document.getElementById('bcIssue').value;
            const expiryDateVal = document.getElementById('bcExpiry').value;
            
            if (issueDateVal && expiryDateVal) {
                const issue = new Date(issueDateVal);
                const expiry = new Date(expiryDateVal);
                
                // Calculate total days between dates, converted to fractional years
                const diffTime = Math.max(0, expiry - issue);
                const diffDays = diffTime / (1000 * 60 * 60 * 24);
                const totalYears = diffDays / 365.25; // Accounting for leap years safely
                
                computedValue = yearlyInterest * totalYears;
            } else {
                computedValue = 0; // Can't calculate maturity return without clear dates
            }
            break;
        default:
            computedValue = 0;
    }

    // Populate field locked to standard financial decimal precision
    document.getElementById('bcInterestValue').value = computedValue.toFixed(2);
}