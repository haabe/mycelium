# What discovery before the build gives you

**Audience**: you have read the README, and you are not convinced yet.
**Time to read**: 8 min.
**Last updated**: 2026-10-01.

The README says what Mycelium does. This page is about the question underneath it. What do you get from finding out before you build that you do not get from building first and finding out after?

## Ten thousand people

On the first of November 1998 a new kind of phone went on sale. It worked anywhere on the planet, off a ring of satellites, and it had taken eleven years and more than five billion dollars to build. The handset cost about three thousand dollars, and calls cost up to eight dollars a minute.

The loans behind it had a condition. By the end of March 1999 the company needed 52,000 subscribers. On the day, it had 10,294. Its own filing to the SEC said its expectations "were incorrect by a substantial amount", and in August 1999 Iridium filed for bankruptcy.

The easy reading is that nobody asked. But that is not what happened. Before launch Iridium screened over 200,000 people and interviewed 23,000 of them in 42 countries. The asking was done once, near the start. Over the next eleven years mobile coverage spread to exactly the business travellers it was for, and the satellite phone still did not work inside cars or buildings. The 1998 prospectus listed the risks across 25 pages. Later, the researchers who studied the collapse found "little evidence" that any of them were addressed. Its interim CEO put it more briefly. "First we created a marvelous technological achievement. Then we asked how to make money on it."

## What finding out first actually buys you

Two randomised trials in Milan and Turin followed 382 founders for five years (Coali, Gambardella and Novelli, *Research Policy*, 2024). One group was trained to write down what they assumed and test it before committing. The trained founders made their first three in ten stop decisions within about 12 weeks. The others took about 18 weeks to get as far. Note that stopping sooner is the good result here, because every week in between was spent building something that would be stopped anyway. By year five the untrained founders had stopped more of their projects, not fewer, 82 percent against 76. And independent experts who rated the abandoned projects found the trained founders had not thrown away good ones.

So skipping discovery does not save you the kill. It moves it later, after you have paid for more of the build. That is the whole economic case, and it is a case about time and spend, not about some multiplier.

A second finding sharpens it. A 2025 working paper pooling eight more trials and 1,556 founders found that experimenting without first stating what you believed gave no significant short-term benefit (Camuffo, Gambardella and Jannace). The test only helped when the assumption was written down before it.

## Research is not the cure

If it were, Iridium would have survived. Three other well-recorded failures went wrong in three different ways.

- **New Coke, 1985.** Coca-Cola ran taste tests with nearly 200,000 people, and the new formula won. The company's own history says what the tests "didn't show" was "the bond consumers felt" with the drink. The research answered the wrong question. Coca-Cola brought the original back 79 days later.
- **Amazon's Fire Phone, 2014.** Amazon's doctrine is to start with the customer and work backwards. Staff who worked on the phone told *Fast Company* that "we were not building the phone for the customer". As one put it, "we were building it for Jeff." It ended in a $170 million charge in Amazon's own filing.
- **Quibi, 2020.** It raised $1.75 billion for short mobile shows and closed within the year. Jeffrey Katzenberg, its founder, told CNBC that "we asked people to pay for it before they actually understood what it was." He also blamed the pandemic, and was honest that he would never know the split.

None of these teams lacked research or smart people. What failed was keeping the question alive. Which assumption are we betting on? Has anyone outside the room tested it? And is the answer still true now that we are about to commit more?

## Doing it by hand is a slippery slope

You probably know all the much-repeated best practices already. Maybe you have tried to do them by hand. A list of assumptions in a doc, a rule to talk to five users before building, or a review before each release. It is like a unicorn sighting. Then there is a deadline. Or the speedy agent. And let's not forget the doc that went stale. And nobody is wrong for skipping it, because there was always a good reason.

The checks are not hard. Keeping them in front of you at the moment you are about to commit is hard. That is the part Mycelium takes over.

## What Mycelium keeps in step with you

Mycelium does not do your discovery. Talking to the people with the problem is still yours. What it does is put the checks inside your agent, at the moments you would otherwise skip them.

- **Before any code.** Four questions, about ten minutes. What is the problem, who has it, what are you assuming, what would show you wrong. The answers go into your repo, where the agent can be held to them.
- **At the first source file.** The agent stops and asks for that evidence before it writes one, and goes quiet once it exists.
- **Before the agent builds on an idea.** The riskiest assumption under it has to have a named test, a sentence on how you would find out, not a label.
- **Before anything reaches real people.** There has to be a record of who will see it, how, and until when, and of the security and privacy checks done for them.
- **On the record.** Every decision is kept, with the evidence it rested on, so later you can see what you tested, what it showed, and what you decided because of it. You can correct a note on a decision. What you cannot do is make an old decision disappear, and Mycelium refuses the write that tries.
- **At the start of each session.** It proposes the one thing most worth doing next, instead of leaving you to remember.

That is Iridium's missing piece, put where your agent works. The question gets asked again before each commitment, not once at the start.

**On a project that already has code**, it does not lock you out of your own work. The first time your agent edits the project it asks once whether you want Mycelium to read it. If you say yes, it drafts what the code can tell it, such as what is being delivered, and names what the code cannot, such as who it is for and whether anyone asked them. That second list is where the work starts.

## Done the other way round

In the early 1990s Intuit noticed something odd in its survey data. Quicken, its personal finance program, was being used in offices to keep the books. Scott Cook, a co-founder, went and talked to those users. "We assumed the paradigm was, of course, they all used accounting. No, they hate accounting." So they built QuickBooks, and sold it as "the first accounting software with no accounting in it."

An assumption, named. Tested on real people, overturned, and the product changed before it was built.

## Where the evidence stops

I'll give you two honest limits.

The famous rule that a bug costs 100 times more to fix in production than in design has no data under it. It goes back to 1981 training notes, and in 2024 the US government's own security advisory committee filed the claim under "Fact or Myth?". Shifting security left is a sound practice resting on practitioner consensus, not on that number. Nothing here gives you a multiplier for discovery either, and you should be suspicious of anyone who does.

And if you can run hundreds of experiments on real traffic, testing after you ship is a real alternative. At Microsoft about a third of the ideas teams believed in enough to build improved the metric they were meant to improve (Kohavi and colleagues). At that volume you can afford to be wrong two out of three times. With a weekend and no users yet, you cannot, so the cheap test has to come before the build.

## What to do next

- **Try it on your next idea.** [Install it and run `/mycelium:start`](get-started.md). Four questions, about ten minutes, and you keep the answers whether you stay or not.
- **Check it is for you first.** If you already know who it is for and that the problem is real, [a lighter tool may suit you better](../README.md#when-to-use-something-else).
- **Evaluating it for a team?** [Give it an hour, with a checklist that is not trying to sell you anything](evaluate.md).
- **Want the reasoning behind the design?** [Why it is opinionated rather than optional](philosophy.md).

## Sources

- Iridium: Iridium LLC, Form 10-Q for Q1 1999 ([SEC EDGAR](https://www.sec.gov/Archives/edgar/data/0000948421/000095013399001884/0000950133-99-001884.txt)); Finkelstein and Sanford, "Learning from Corporate Mistakes: The Rise and Fall of Iridium", *Organizational Dynamics* 29(2), 2000, which is also where the interim CEO is quoted.
- Coali, Gambardella and Novelli, "Scientific decision-making, project selection and longer-term outcomes", *Research Policy* 53(6), 2024 ([doi](https://doi.org/10.1016/j.respol.2024.105022)).
- Camuffo, Gambardella and Jannace, CEPR Discussion Paper 20300, 2025 (working paper).
- New Coke: [The Coca-Cola Company's own history page](https://www.coca-colacompany.com/about-us/history/new-coke-the-most-memorable-marketing-blunder-ever).
- Fire Phone: Amazon, Form 10-Q for Q3 2014; Austin Carr, "The Real Story Behind Jeff Bezos's Fire Phone Debacle", *Fast Company*, January 2015.
- Quibi: Jeffrey Katzenberg on CNBC, 22 October 2020.
- QuickBooks: Scott Cook in conversation at the [Wisconsin School of Business](https://business.wisc.edu/news/savor-surprises-a-conversation-with-intuit-co-founder-scott-cook/), 2022.
- The cost-of-defect curve: CISA Cybersecurity Advisory Committee report, October 2024; Laurent Bossavit, *The Leprechauns of Software Engineering*.
- Kohavi, Crook and Longbotham, "Online Experimentation at Microsoft", 2009.
