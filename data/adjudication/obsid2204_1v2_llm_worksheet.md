# Adjudication worksheet — obsid 2204

Teacher 309 · year 2 · 353 turns (172 teacher) · coders 1 vs 2 vs llm

## Coverage

| coder | flags | attested through | marked complete |
|---|---|---|---|
| 1 | 4 | turn 227 | **no** |
| 2 | 10 | turn 227 | **no** |
| llm | 3 | full transcript | yes |

> **62 teacher turns (36%) sit past turn 227, where neither coder has a flag and neither is marked complete.** Treat that range as uncoded, not as agreed-empty. Rows below are restricted to turns 1–227.

## Agreement

Computed over 110 teacher turns in turns 1–227.

| stat | value |
|---|---|
| both flagged | 4 |
| only coder 1 | 0 |
| only coder 2 | 6 |
| **positive agreement** (headline) | **0.571** |
| Cohen's κ | 0.548 |
| PABAK | 0.891 |
| raw agreement (inflated) | 0.945 |
| category Jaccard, shared turns | 0.725 |

Do not report κ alone — see `tools/coder/README.md`.

### Threshold or definition?

Smaller flag set: 4. Larger: 10. Containment of smaller in larger: **100%**.

> High containment with unequal sizes — this reads as a **threshold** difference: one coder requires more evidence before flagging. Settle on how strong a cue has to be before it counts, and the category work will mostly follow.

Per category (union of flagged turns in scope):

| cat | both | only 1 | only 2 |
|---|---|---|---|
| A | 0 | 0 | 4 |
| B | 0 | 1 | 0 |
| D | 2 | 2 | 3 |
| E | 1 | 0 | 0 |
| F | 2 | 0 | 2 |
| G | 0 | 0 | 1 |

## Turns to resolve

10 turns. Work top to bottom; fill in **Decision** as you go, then transfer to `obsid2204_1v2_llm_worksheet.csv`.

### Turn 9 — ONLY-2

-    `t7` **teacher**: thinking now that s one of the word strategy is thinking all right and you know math when you have to do it you have to think go on your turn
-    `t8` **student**: and using prior knowledge
- **→** `t9` **teacher**: and using prior knowledge i like that strategy is using your prior knowledge and kind of put it together yes what about you come on don t get mad tell me using prior knowledge all right what else okay that s fine anybody else context closed so these are the things we re going to focus on prior knowledge thinking i m thinking i use my prior knowledge and i use the context now let me show you something quick very quick what strategy do i use we are going to work on several kind of problem today and we re gonna use these our blocks to help us i m gonna use them first but i m gonna let you use them but another thing we re going to use we re going to use let me show you these are all to help you and i m going to show you how to use them to get a strategy going that s been our thinking i m going to use this one and i m gonna let you use one when it s time when it s time so i m gonna use this one to figure out what how many how many see he s not willing how many
-    `t10` **teacher**: how many now
-    `t11` **multiple students**: strategies

- **Coder 1:** did not flag
- **Coder 2:** D (low)  
  _note:_ “see he s not willing how many”. This is incomplete; maybe the teacher thinks the student doesn't want to try to explore or answer (flag to discuss)
- **Coder llm:** did not flag

**Decision:** categories ______  include in gold standard: Y / N  
**Rule this establishes:** ____________________________________

### Turn 54 — ONLY-2+llm

-    `t52` **teacher**: how many groups that s the question and you need to be careful you need to watch that now listen i m giving you a situation these are the things now this is your own thinking that s what i want you to pay attention they give me uh unh uh hm now you what what is my situation what is my situation here i need help i need your help what is my situation now i see people counting people are counting and they say now people are raising their hand that s nice see nice nice now yes i see people talking to each other that s fine too people are telling this array must be hm and i m going to put it in the middle
-    `t53` **student**: inaudible
- **→** `t54` **teacher**: yes student m student m good job now it s time i like the way you talk to each other ah you don t need this one don t we you need help all morning you don t know your timetable that s when you do
-    `t55` **student**: no i do
-    `t56` **teacher**: right now student m is the person

- **Coder 1:** did not flag
- **Coder 2:** A (low)
- **Coder llm:** B (low)  
  _note:_ The teacher frames a named student by a lack ('you don't know your timetable' / needing help 'all morning'), though phrasing is somewhat ambiguous and jocular.  
  _span:_ “you need help all morning you don t know your timetable”

**Decision:** categories ______  include in gold standard: Y / N  
**Rule this establishes:** ____________________________________

### Turn 62 — ONLY-2

-    `t60` **student**: eight nine four
-    `t61` **student**: yes
- **→** `t62` **teacher**: now excuse me he s not paying attention yep eight times four right because i have one two three four and i put my four here and sometime they give me this one and they say hey name the hm and the see eight times four so all right student f all right now eight times four and what
-    `t63` **student**: thirty two
-    `t64` **multiple students**: thirty two

- **Coder 1:** did not flag
- **Coder 2:** D (medium)
- **Coder llm:** did not flag

**Decision:** categories ______  include in gold standard: Y / N  
**Rule this establishes:** ____________________________________

### Turn 67 — ONLY-1+2

-    `t65` **teacher**: eight times all right you said it see we re not arguing over that now are we arguing we could just count
-    `t66` **student**: teacher the funny thing is it says 32 right there on top it says 32 right there
- **→** `t67` **teacher**: does it i really will pay attention to that now my good learners that are thinking see student f is thinking but he s turning back now student f i need your attention up here so listen sometime they just give me this and they give me this i want you to think use your strategy of thinking see some people are turning back looking at other people i need your attention to the front now sometime they just give me this and that hmm and now this way this way this way look at that some people are thinking but they re not thinking they re playing with i know you re a good thinker student f i know you re a good thinker but
-    `t68` **student**: inaudible
-    `t69` **teacher**: surprise they give me this and that and i have to hm what is hm see she is still talking see they give me this and that i know when it s time to talk i ll let you talk but now they give me this and that and they want me to figure out this some people already know what does that mean what am i supposed to do what am i supposed to be thinking because remember this is the thing now i want you to talk to your friend and make problem write an hm problem write a hm problem now student d you need to talk to the person next to you only yes the problem i want you to think of the division problem one minute one minute student r with the person next you think over the problem we only have a minute see i see these people talking those are talking good job yep

- **Coder 1:** D, F (medium)  
  _note:_ "now my good learners that are thinking see student f is thinking but he s turning back now student f i need your attention up here"
- **Coder 2:** F (high)
- **Coder llm:** did not flag

**Decision:** categories ______  include in gold standard: Y / N  
**Rule this establishes:** ____________________________________

### Turn 144 — ONLY-2

-    `t142` **teacher**: three left i like the word three left and in division we call the three left
-    `t143` **student**: remainder
- **→** `t144` **teacher**: remainder that s the word i was getting to see student o did you get a look at that that s the thing after we divided equally there is three more with if i have the situation there a lot of time they give you division like that on purpose and they would say what can i do now the situation is we re going on a field trip what do i do with the three remainder people three left over what can i do with these three people now i want you to think of a situation student a i m going on a field trip i have 35 people and we only have four cars yes i see people thinking now you re all thinking you don t need to talk to anyone see we re going on a field trip and i know some people they are smart like student d he is thinking of a situation now student f let s see people that are thinking we re going on a field trip we will have four cars or four buses for the 32 or 35 people it s not 32 anymore it s 35 the situation see you need to think of if it s a situation when it s 35 it s not apples that we have to share now we will think of it s apple 35 apple but let s think of the time this time student m it s 35 people going on the field trip 35 students or 35 of us any could be teachers could be people could be anybody and we re going on a field trip see i see he s figuring it out then what do we do with this 3 people out of 35 all right so lot of people already think so student s what do you think we could do with these three people
-    `t145` **student**: the people that are here take one in each one
-    `t146` **teacher**: one in each bus she said i could take one of these and add to this one but how about if the bus can t take anymore see we re thinking it s only thinking so that would be three buses that have an extra person maybe that s the case maybe you could explain it that way and sometime they ask you hey explain what did you think we could do it s only your own thinking now another person said what could you do

- **Coder 1:** did not flag
- **Coder 2:** A, F (medium)  
  _note:_ "i know some people they are smart like student d". It implies that others do not fall into this category.
- **Coder llm:** did not flag

**Decision:** categories ______  include in gold standard: Y / N  
**Rule this establishes:** ____________________________________

### Turn 148 — ONLY-2

-    `t146` **teacher**: one in each bus she said i could take one of these and add to this one but how about if the bus can t take anymore see we re thinking it s only thinking so that would be three buses that have an extra person maybe that s the case maybe you could explain it that way and sometime they ask you hey explain what did you think we could do it s only your own thinking now another person said what could you do
-    `t147` **student**: you could like take some kids and bring them back and just come back and get the rest
- **→** `t148` **teacher**: come back and get the rest wouldn t it just be one of the bus say oh i ll have to make a trip back and get the three of them by themselves probably now no you talk already let me think of student o think oh good job student o let me see somebody else who was thinking i know the smart one always thinking yes you could
-    `t149` **student**: you could like the children that s extra
-    `t150` **teacher**: the three extra what could you do with them

- **Coder 1:** did not flag
- **Coder 2:** A, F (low)  
  _note:_ "i know the smart one always thinking", labeling some students with a fixed ability tag of smart
- **Coder llm:** did not flag

**Decision:** categories ______  include in gold standard: Y / N  
**Rule this establishes:** ____________________________________

### Turn 156 — AGREE

-    `t154` **teacher**: oh you could ve asked a mom to come with their car and kind of take one person or drive a few or drive three because if it s a passenger car it might be able to take three people in the back that could be true we are thinking when it s remainder we need to think of a situation now let s think of a different situation now we re thinking of situation strategies in our head let me see student c is thinking my favorite student f student f is thinking now listen i m giving you a different situation it is sharing thing it s sharing we have apple we have candy we have cupcakes like people said but we have 35 to share in total
-    `t155` **student**: donuts
- **→** `t156` **teacher**: donuts anything that could share now we got no we re thinking of anything that we could share maybe it s candy maybe it s donuts maybe it s cake maybe it s cupcakes i just need your thinking now if it s a sharing thing what could we do with the three cupcakes that are left what can we do it s a sharing thing what can we do with the three cupcakes good job some people are thinking see i don t see student c thinking i know she s not and my let s see student w
-    `t157` **student**: yep
-    `t158` **teacher**: i don t see you thinking it s a different situation it s food it s candy it s cupcakes all right what can we do with the three extra we know we know yeah student m

- **Coder 1:** D (low)  
  _note:_ "she isn't trying / thinking"
- **Coder 2:** D (medium)  
  _note:_ "i don t see student c thinking i know she s not"
- **Coder llm:** D (medium)  
  _note:_ The teacher characterizes a named student as simply 'not thinking' rather than describing a specific behavior or offering support, attributing a lack of engagement to the student.  
  _span:_ “see i don t see student c thinking i know she s not”

**Decision:** categories ______  include in gold standard: Y / N  
**Rule this establishes:** ____________________________________

### Turn 158 — ONLY-1+2

-    `t156` **teacher**: donuts anything that could share now we got no we re thinking of anything that we could share maybe it s candy maybe it s donuts maybe it s cake maybe it s cupcakes i just need your thinking now if it s a sharing thing what could we do with the three cupcakes that are left what can we do it s a sharing thing what can we do with the three cupcakes good job some people are thinking see i don t see student c thinking i know she s not and my let s see student w
-    `t157` **student**: yep
- **→** `t158` **teacher**: i don t see you thinking it s a different situation it s food it s candy it s cupcakes all right what can we do with the three extra we know we know yeah student m
-    `t159` **student**: you can give them
-    `t160` **teacher**: you know we don t do that

- **Coder 1:** D (medium)  
  _note:_ "i don t see you thinking it s a different situation"
- **Coder 2:** D (medium)  
  _note:_ "i don t see you thinking." Terrible statement to be heard by a student from a math teacher
- **Coder llm:** did not flag

**Decision:** categories ______  include in gold standard: Y / N  
**Rule this establishes:** ____________________________________

### Turn 164 — ONLY-2

-    `t162` **teacher**: wait a minute we know it will be divided into four groups in this situation we have three more three extra three leftover cupcakes if it s cupcakes then what can we do with the three cupcakes that remain and we call them remainder all right in division like that we always have situation where we have some leftover and we call them remainder and the problem you ll have to do will have a difference it s a situation where we will use the remainder right good job see those people are very very polite they raise their hand student c what can you do with the three remainder
-    `t163` **student**: inaudible
- **→** `t164` **teacher**: you save it you save it for them to share because we remember we have a it goes into four groups that s 35 and we have this four groups each of them has eight think about it the problem is i have 35 cupcakes student c i have 35 cupcakes and i have to divided them into four people each of them will get eight but there will be three student r there will be three left over you know i hate to see student w is working on it but she s not telling me what s she s thinking student w
-    `t165` **student**: inaudible
-    `t166` **teacher**: the three left over could

- **Coder 1:** did not flag
- **Coder 2:** D, G (medium)  
  _note:_ "you know i hate to see student w is working on it but she s not telling me what s she s thinking student w"
- **Coder llm:** did not flag

**Decision:** categories ______  include in gold standard: Y / N  
**Rule this establishes:** ____________________________________

### Turn 227 — CATEGORY-DIFF

-    `t225` **teacher**: is the thing into eight vans
-    `t226` **student**: eight vans that would be
- **→** `t227` **teacher**: now hold on another way 44 people some people are not see 44 into that s another word into another way of writing into into 8 yeah 44 people into see this into she s not paying attention to me into two ways of writing it for 44 people into a group you could yeah 44 people into a group into a group into a group sometime you find it written that way but most of the time it s this way that means into now we learn yesterday after they write it this way you ll write it that way yourself those people that are not paying attention are the ones that won t be able to do it we know that if you cannot see i could tell ones that will be able to do it yep like student m and c doesn t go like this she goes like yeah remember we said that seating is really this way all right so we said hey
-    `t228` **student**: inaudible
-    `t229` **teacher**: you can t see all right go this way we could say we already know if i have 44 and i see my 40 and i know my time table and i know i m gonna time hm to get hm yeah did i do it that way now how many eight into

- **Coder 1:** B, D, E, F (medium)  
  _note:_ those people that are not paying attention are the ones that won t be able to do it we know that if you cannot see i could tell ones that will be able to do it - dividing the class into will-succeed / won't succeed
- **Coder 2:** A, E, F (high)  
  _note:_ "those people that are not paying attention are the ones that won t be able to do it we know that if you cannot see i could tell ones that will be able to do it yep like student m and c doesn t go like this "
- **Coder llm:** D, E (high)  
  _note:_ The teacher attributes anticipated failure to students based on behavior and predicts who 'will' and 'won't be able to do it,' sorting students by perceived inability rather than describing the task or effort.  
  _span:_ “those people that are not paying attention are the ones that won t be able to do it we know that if you cannot see i could tell ones that will be able to do it”

**Decision:** categories ______  include in gold standard: Y / N  
**Rule this establishes:** ____________________________________
