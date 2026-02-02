document.addEventListener('DOMContentLoaded', function () {
    const quotes = [
        {
            text: "AI will not replace you. A person using AI will.",
            author: "Industry Saying"
        },
        {
            text: "The best way to predict the future is to invent it.",
            author: "Alan Kay"
        },
        {
            text: "Technology is best when it brings people together.",
            author: "Matt Mullenweg"
        },
        {
            text: "It's not a faith in technology. It's faith in people.",
            author: "Steve Jobs"
        },
        {
            text: "The science of today is the technology of tomorrow.",
            author: "Edward Teller"
        },
        {
            text: "First, solve the problem. Then, write the code.",
            author: "John Johnson"
        },
        {
            text: "Innovation distinguishes between a leader and a follower.",
            author: "Steve Jobs"
        },
        {
            text: "Simplicity is the ultimate sophistication.",
            author: "Leonardo da Vinci"
        }
    ];

    const quoteTextElement = document.getElementById('quote-text');
    const quoteAuthorElement = document.getElementById('quote-author');

    if (quoteTextElement && quoteAuthorElement) {
        // Select a random quote
        const randomIndex = Math.floor(Math.random() * quotes.length);
        const randomQuote = quotes[randomIndex];

        // Apply the quote with a fade-in effect (if desired, or just text replacement)
        quoteTextElement.textContent = `"${randomQuote.text}"`;
        quoteAuthorElement.textContent = `— ${randomQuote.author}`;
    }
});
