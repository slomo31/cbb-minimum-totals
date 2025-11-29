#!/usr/bin/env python3
"""
Comprehensive College Basketball Team Name Matcher

This module provides robust team name matching for college basketball,
handling the many variations in how teams are named across different
data sources (Odds API, NCAA API, Barttorvik, etc.)

The approach:
1. Build a master list of all D1 teams with their canonical names
2. Create multiple lookup keys for each team (abbreviations, mascots, locations)
3. Use fuzzy matching only as a last resort
"""

# Master team database - canonical name : [all possible variations]
# Canonical names should match Barttorvik format
TEAM_DATABASE = {
    # === A ===
    'Abilene Christian': ['abilene christian', 'abilene christian wildcats', 'acu'],
    'Air Force': ['air force', 'air force falcons'],
    'Akron': ['akron', 'akron zips'],
    'Alabama': ['alabama', 'alabama crimson tide', 'bama'],
    'Alabama A&M': ['alabama a&m', 'alabama a&m bulldogs', 'aamu'],
    'Alabama St.': ['alabama state', 'alabama st', 'alabama st.', 'alabama state hornets'],
    'Albany': ['albany', 'albany great danes', 'ualbany'],
    'Alcorn St.': ['alcorn state', 'alcorn st', 'alcorn st.', 'alcorn state braves'],
    'American': ['american', 'american university', 'american eagles'],
    'Appalachian St.': ['appalachian state', 'appalachian st', 'appalachian st.', 'app state', 'app st', 'appalachian state mountaineers'],
    'Arizona': ['arizona', 'arizona wildcats', 'u of a', 'uofa'],
    'Arizona St.': ['arizona state', 'arizona st', 'arizona st.', 'asu', 'arizona state sun devils'],
    'Arkansas': ['arkansas', 'arkansas razorbacks', 'razorbacks'],
    'Arkansas St.': ['arkansas state', 'arkansas st', 'arkansas st.', 'arkansas state red wolves', 'a-state'],
    'Arkansas-Pine Bluff': ['arkansas pine bluff', 'arkansas-pine bluff', 'uapb', 'arkansas pine bluff golden lions'],
    'Army': ['army', 'army west point', 'army black knights'],
    'Auburn': ['auburn', 'auburn tigers'],
    'Austin Peay': ['austin peay', 'austin peay governors', 'austin peay state'],
    
    # === B ===
    'Ball St.': ['ball state', 'ball st', 'ball st.', 'ball state cardinals'],
    'Baylor': ['baylor', 'baylor bears'],
    'Bellarmine': ['bellarmine', 'bellarmine knights'],
    'Belmont': ['belmont', 'belmont bruins'],
    'Bethune-Cookman': ['bethune cookman', 'bethune-cookman', 'bethune-cookman wildcats', 'b-cu'],
    'Binghamton': ['binghamton', 'binghamton bearcats'],
    'Boise St.': ['boise state', 'boise st', 'boise st.', 'boise state broncos'],
    'Boston College': ['boston college', 'boston college eagles', 'bc'],
    'Boston University': ['boston university', 'boston u', 'boston u.', 'bu', 'boston university terriers', 'boston univ'],
    'Bowling Green': ['bowling green', 'bowling green falcons', 'bgsu', 'bowling green state'],
    'Bradley': ['bradley', 'bradley braves'],
    'Brown': ['brown', 'brown bears'],
    'Bryant': ['bryant', 'bryant bulldogs'],
    'Bucknell': ['bucknell', 'bucknell bison'],
    'Buffalo': ['buffalo', 'buffalo bulls', 'ub'],
    'Butler': ['butler', 'butler bulldogs'],
    'BYU': ['byu', 'brigham young', 'brigham young cougars'],
    
    # === C ===
    'Cal Baptist': ['cal baptist', 'california baptist', 'cal baptist lancers', 'cbu'],
    'Cal Poly': ['cal poly', 'cal poly mustangs', 'cal poly slo'],
    'Cal St. Bakersfield': ['cal state bakersfield', 'csub', 'csu bakersfield', 'cal st bakersfield', 'cal st. bakersfield', 'csub roadrunners'],
    'Cal St. Fullerton': ['cal state fullerton', 'csuf', 'csu fullerton', 'cal st fullerton', 'cal st. fullerton', 'fullerton'],
    'Cal St. Northridge': ['cal state northridge', 'csun', 'northridge', 'cal st northridge', 'cal st. northridge'],
    'California': ['california', 'cal', 'cal bears', 'california golden bears', 'uc berkeley', 'berkeley'],
    'Campbell': ['campbell', 'campbell fighting camels'],
    'Canisius': ['canisius', 'canisius golden griffins'],
    'Central Arkansas': ['central arkansas', 'uca', 'central arkansas bears'],
    'Central Connecticut': ['central connecticut', 'central connecticut state', 'ccsu', 'central connecticut st', 'central conn', 'central connecticut blue devils'],
    'Central Florida': ['ucf', 'central florida', 'ucf knights'],
    'Central Michigan': ['central michigan', 'central michigan chippewas', 'cmu'],
    'Charleston': ['charleston', 'college of charleston', 'charleston cougars', 'cofc'],
    'Charleston Southern': ['charleston southern', 'charleston southern buccaneers'],
    'Charlotte': ['charlotte', 'unc charlotte', 'charlotte 49ers'],
    'Chattanooga': ['chattanooga', 'chattanooga mocs', 'utc'],
    'Chicago St.': ['chicago state', 'chicago st', 'chicago st.', 'chicago state cougars'],
    'Cincinnati': ['cincinnati', 'cincinnati bearcats', 'cincy', 'uc'],
    'Clemson': ['clemson', 'clemson tigers'],
    'Cleveland St.': ['cleveland state', 'cleveland st', 'cleveland st.', 'cleveland state vikings'],
    'Coastal Carolina': ['coastal carolina', 'coastal carolina chanticleers', 'coastal', 'ccu'],
    'Colgate': ['colgate', 'colgate raiders'],
    'Colorado': ['colorado', 'colorado buffaloes', 'cu', 'buffs'],
    'Colorado St.': ['colorado state', 'colorado st', 'colorado st.', 'colorado state rams', 'csu rams'],
    'Columbia': ['columbia', 'columbia lions'],
    'Connecticut': ['connecticut', 'uconn', 'uconn huskies', 'connecticut huskies'],
    'Coppin St.': ['coppin state', 'coppin st', 'coppin st.', 'coppin state eagles'],
    'Cornell': ['cornell', 'cornell big red'],
    'Creighton': ['creighton', 'creighton bluejays'],
    
    # === D ===
    'Dartmouth': ['dartmouth', 'dartmouth big green'],
    'Davidson': ['davidson', 'davidson wildcats'],
    'Dayton': ['dayton', 'dayton flyers'],
    'Delaware': ['delaware', 'delaware blue hens', 'ud'],
    'Delaware St.': ['delaware state', 'delaware st', 'delaware st.', 'delaware state hornets', 'dsu'],
    'Denver': ['denver', 'denver pioneers'],
    'DePaul': ['depaul', 'depaul blue demons'],
    'Detroit Mercy': ['detroit mercy', 'detroit', 'detroit mercy titans', 'detroit titans'],
    'Drake': ['drake', 'drake bulldogs'],
    'Drexel': ['drexel', 'drexel dragons'],
    'Duke': ['duke', 'duke blue devils'],
    'Duquesne': ['duquesne', 'duquesne dukes'],
    
    # === E ===
    'East Carolina': ['east carolina', 'east carolina pirates', 'ecu'],
    'East Tennessee St.': ['east tennessee state', 'east tennessee st', 'etsu', 'east tennessee st.'],
    'Eastern Illinois': ['eastern illinois', 'eastern illinois panthers', 'eiu'],
    'Eastern Kentucky': ['eastern kentucky', 'eastern kentucky colonels', 'eku'],
    'Eastern Michigan': ['eastern michigan', 'eastern michigan eagles', 'emu'],
    'Eastern Washington': ['eastern washington', 'eastern washington eagles', 'ewu'],
    'Elon': ['elon', 'elon phoenix'],
    'Evansville': ['evansville', 'evansville purple aces'],
    
    # === F ===
    'Fairfield': ['fairfield', 'fairfield stags'],
    'Fairleigh Dickinson': ['fairleigh dickinson', 'fdu', 'fairleigh dickinson knights'],
    'FIU': ['fiu', 'florida international', 'florida international panthers', 'fiu panthers'],
    'Florida': ['florida', 'florida gators', 'uf', 'gators'],
    'Florida A&M': ['florida a&m', 'famu', 'florida a&m rattlers'],
    'Florida Atlantic': ['florida atlantic', 'fau', 'florida atlantic owls', 'fau owls'],
    'Florida Gulf Coast': ['florida gulf coast', 'fgcu', 'florida gulf coast eagles'],
    'Florida St.': ['florida state', 'florida st', 'florida st.', 'fsu', 'florida state seminoles', 'fsu seminoles'],
    'Fordham': ['fordham', 'fordham rams'],
    'Fresno St.': ['fresno state', 'fresno st', 'fresno st.', 'fresno state bulldogs'],
    'Furman': ['furman', 'furman paladins'],
    
    # === G ===
    'Gardner-Webb': ['gardner webb', 'gardner-webb', 'gardner-webb runnin bulldogs'],
    'George Mason': ['george mason', 'george mason patriots', 'gmu'],
    'George Washington': ['george washington', 'george washington colonials', 'gwu', 'gw'],
    'Georgetown': ['georgetown', 'georgetown hoyas', 'hoyas'],
    'Georgia': ['georgia', 'georgia bulldogs', 'uga', 'dawgs'],
    'Georgia Southern': ['georgia southern', 'georgia southern eagles'],
    'Georgia St.': ['georgia state', 'georgia st', 'georgia st.', 'georgia state panthers', 'gsu'],
    'Georgia Tech': ['georgia tech', 'georgia tech yellow jackets', 'gt', 'yellow jackets'],
    'Gonzaga': ['gonzaga', 'gonzaga bulldogs', 'zags'],
    'Grambling St.': ['grambling state', 'grambling st', 'grambling st.', 'grambling', 'grambling state tigers'],
    'Grand Canyon': ['grand canyon', 'grand canyon antelopes', 'gcu'],
    'Green Bay': ['green bay', 'uw green bay', 'green bay phoenix', 'uwgb'],
    
    # === H ===
    'Hampton': ['hampton', 'hampton pirates'],
    'Hartford': ['hartford', 'hartford hawks'],
    'Harvard': ['harvard', 'harvard crimson'],
    'Hawaii': ['hawaii', 'hawai\'i', 'hawaii rainbow warriors', 'uh'],
    'High Point': ['high point', 'high point panthers'],
    'Hofstra': ['hofstra', 'hofstra pride'],
    'Holy Cross': ['holy cross', 'holy cross crusaders'],
    'Houston': ['houston', 'houston cougars', 'uh', 'cougars'],
    'Houston Christian': ['houston christian', 'houston christian huskies', 'hcu', 'houston baptist'],
    'Howard': ['howard', 'howard bison'],
    
    # === I ===
    'Idaho': ['idaho', 'idaho vandals', 'u of i'],
    'Idaho St.': ['idaho state', 'idaho st', 'idaho st.', 'idaho state bengals', 'isu bengals'],
    'Illinois': ['illinois', 'illinois fighting illini', 'u of i', 'illini'],
    'Illinois St.': ['illinois state', 'illinois st', 'illinois st.', 'illinois state redbirds'],
    'Incarnate Word': ['incarnate word', 'uiw', 'incarnate word cardinals'],
    'Indiana': ['indiana', 'indiana hoosiers', 'iu', 'hoosiers'],
    'Indiana St.': ['indiana state', 'indiana st', 'indiana st.', 'indiana state sycamores'],
    'Iona': ['iona', 'iona gaels'],
    'Iowa': ['iowa', 'iowa hawkeyes', 'hawkeyes'],
    'Iowa St.': ['iowa state', 'iowa st', 'iowa st.', 'iowa state cyclones', 'cyclones'],
    'IUPUI': ['iupui', 'iupui jaguars'],
    
    # === J ===
    'Jackson St.': ['jackson state', 'jackson st', 'jackson st.', 'jackson state tigers', 'jsu'],
    'Jacksonville': ['jacksonville', 'jacksonville dolphins', 'ju'],
    'Jacksonville St.': ['jacksonville state', 'jacksonville st', 'jacksonville st.', 'jacksonville state gamecocks', 'jax state'],
    'James Madison': ['james madison', 'jmu', 'james madison dukes'],
    
    # === K ===
    'Kansas': ['kansas', 'kansas jayhawks', 'ku', 'jayhawks'],
    'Kansas St.': ['kansas state', 'kansas st', 'kansas st.', 'k-state', 'ksu', 'kansas state wildcats'],
    'Kennesaw St.': ['kennesaw state', 'kennesaw st', 'kennesaw st.', 'kennesaw', 'kennesaw state owls'],
    'Kent St.': ['kent state', 'kent st', 'kent st.', 'kent state golden flashes'],
    'Kentucky': ['kentucky', 'kentucky wildcats', 'uk', 'wildcats'],
    
    # === L ===
    'La Salle': ['la salle', 'la salle explorers', 'lasalle'],
    'Lafayette': ['lafayette', 'lafayette leopards'],
    'Lamar': ['lamar', 'lamar cardinals'],
    'Le Moyne': ['le moyne', 'lemoyne', 'le moyne dolphins'],
    'Lehigh': ['lehigh', 'lehigh mountain hawks'],
    'Liberty': ['liberty', 'liberty flames'],
    'Lindenwood': ['lindenwood', 'lindenwood lions'],
    'Lipscomb': ['lipscomb', 'lipscomb bisons'],
    'Little Rock': ['little rock', 'ualr', 'arkansas little rock', 'little rock trojans'],
    'Long Beach St.': ['long beach state', 'long beach st', 'long beach st.', 'lbsu', 'long beach state 49ers', 'long beach'],
    'Long Island': ['long island', 'liu', 'long island sharks', 'liu sharks'],
    'Longwood': ['longwood', 'longwood lancers'],
    'Louisiana': ['louisiana', 'louisiana ragin cajuns', 'ull', 'louisiana-lafayette', 'ul lafayette', 'ragin cajuns'],
    'Louisiana Tech': ['louisiana tech', 'la tech', 'louisiana tech bulldogs'],
    'Louisville': ['louisville', 'louisville cardinals', 'uofl', 'cards'],
    'Loyola Chicago': ['loyola chicago', 'loyola (chi)', 'loyola-chicago', 'loyola chicago ramblers', 'loyola il'],
    'Loyola Marymount': ['loyola marymount', 'lmu', 'loyola marymount lions', 'lmu lions'],
    'Loyola Maryland': ['loyola maryland', 'loyola md', 'loyola maryland greyhounds'],
    'LSU': ['lsu', 'louisiana state', 'lsu tigers'],
    
    # === M ===
    'Maine': ['maine', 'maine black bears'],
    'Manhattan': ['manhattan', 'manhattan jaspers'],
    'Marist': ['marist', 'marist red foxes'],
    'Marquette': ['marquette', 'marquette golden eagles'],
    'Marshall': ['marshall', 'marshall thundering herd'],
    'Maryland': ['maryland', 'maryland terrapins', 'terps', 'umd'],
    'Maryland-Eastern Shore': ['maryland eastern shore', 'umes', 'maryland-eastern shore'],
    'Massachusetts': ['massachusetts', 'umass', 'umass minutemen', 'minutemen'],
    'McNeese St.': ['mcneese state', 'mcneese st', 'mcneese st.', 'mcneese', 'mcneese state cowboys'],
    'Memphis': ['memphis', 'memphis tigers'],
    'Mercer': ['mercer', 'mercer bears'],
    'Merrimack': ['merrimack', 'merrimack warriors'],
    'Miami FL': ['miami', 'miami hurricanes', 'miami fl', 'miami (fl)', 'the u', 'um'],
    'Miami OH': ['miami ohio', 'miami oh', 'miami (oh)', 'miami redhawks', 'miami of ohio'],
    'Michigan': ['michigan', 'michigan wolverines', 'um', 'wolverines'],
    'Michigan St.': ['michigan state', 'michigan st', 'michigan st.', 'msu', 'michigan state spartans', 'spartans'],
    'Middle Tennessee': ['middle tennessee', 'mtsu', 'middle tennessee state', 'middle tennessee blue raiders'],
    'Milwaukee': ['milwaukee', 'uw milwaukee', 'uwm', 'milwaukee panthers'],
    'Minnesota': ['minnesota', 'minnesota golden gophers', 'gophers', 'u of m'],
    'Mississippi St.': ['mississippi state', 'mississippi st', 'mississippi st.', 'miss state', 'mississippi state bulldogs', 'msu bulldogs'],
    'Mississippi': ['mississippi', 'ole miss', 'ole miss rebels', 'miss'],
    'Mississippi Valley St.': ['mississippi valley state', 'mvsu', 'miss valley st', 'mississippi valley st', 'mississippi valley st.'],
    'Missouri': ['missouri', 'missouri tigers', 'mizzou'],
    'Missouri St.': ['missouri state', 'missouri st', 'missouri st.', 'missouri state bears'],
    'Monmouth': ['monmouth', 'monmouth hawks'],
    'Montana': ['montana', 'montana grizzlies', 'um'],
    'Montana St.': ['montana state', 'montana st', 'montana st.', 'montana state bobcats'],
    'Morehead St.': ['morehead state', 'morehead st', 'morehead st.', 'morehead state eagles'],
    'Morgan St.': ['morgan state', 'morgan st', 'morgan st.', 'morgan state bears'],
    'Mount St. Mary\'s': ['mount st marys', 'mount st. mary\'s', 'mt st marys', 'mt. st. mary\'s', 'the mount', 'mountaineers'],
    'Murray St.': ['murray state', 'murray st', 'murray st.', 'murray state racers'],
    
    # === N ===
    'Navy': ['navy', 'navy midshipmen', 'naval academy'],
    'NC A&T': ['nc a&t', 'north carolina a&t', 'nc a&t aggies', 'ncat'],
    'NC Central': ['nc central', 'north carolina central', 'nccu', 'north carolina central eagles'],
    'NC State': ['nc state', 'north carolina state', 'n.c. state', 'nc state wolfpack', 'wolfpack'],
    'Nebraska': ['nebraska', 'nebraska cornhuskers', 'huskers'],
    'Nevada': ['nevada', 'nevada wolf pack', 'unr'],
    'New Hampshire': ['new hampshire', 'unh', 'new hampshire wildcats'],
    'New Mexico': ['new mexico', 'new mexico lobos', 'unm', 'lobos'],
    'New Mexico St.': ['new mexico state', 'new mexico st', 'new mexico st.', 'nmsu', 'new mexico state aggies'],
    'New Orleans': ['new orleans', 'uno', 'new orleans privateers'],
    'Niagara': ['niagara', 'niagara purple eagles'],
    'Nicholls St.': ['nicholls state', 'nicholls st', 'nicholls st.', 'nicholls', 'nicholls state colonels'],
    'NJIT': ['njit', 'njit highlanders', 'new jersey tech'],
    'Norfolk St.': ['norfolk state', 'norfolk st', 'norfolk st.', 'norfolk state spartans'],
    'North Alabama': ['north alabama', 'una', 'north alabama lions'],
    'North Carolina': ['north carolina', 'unc', 'tar heels', 'carolina', 'north carolina tar heels'],
    'North Dakota': ['north dakota', 'und', 'north dakota fighting hawks'],
    'North Dakota St.': ['north dakota state', 'north dakota st', 'north dakota st.', 'ndsu', 'north dakota state bison'],
    'North Florida': ['north florida', 'unf', 'north florida ospreys'],
    'North Texas': ['north texas', 'unt', 'north texas mean green', 'mean green'],
    'Northeastern': ['northeastern', 'northeastern huskies', 'neu'],
    'Northern Arizona': ['northern arizona', 'nau', 'northern arizona lumberjacks'],
    'Northern Colorado': ['northern colorado', 'unc bears', 'northern colorado bears'],
    'Northern Illinois': ['northern illinois', 'niu', 'northern illinois huskies'],
    'Northern Iowa': ['northern iowa', 'uni', 'northern iowa panthers', 'n iowa', 'n. iowa'],
    'Northern Kentucky': ['northern kentucky', 'nku', 'northern kentucky norse'],
    'Northwestern': ['northwestern', 'northwestern wildcats'],
    'Northwestern St.': ['northwestern state', 'northwestern st', 'northwestern st.', 'nsula', 'northwestern state demons'],
    'Notre Dame': ['notre dame', 'notre dame fighting irish', 'nd', 'irish'],
    
    # === O ===
    'Oakland': ['oakland', 'oakland golden grizzlies'],
    'Ohio': ['ohio', 'ohio bobcats', 'ohio university', 'ohio u'],
    'Ohio St.': ['ohio state', 'ohio st', 'ohio st.', 'osu', 'ohio state buckeyes', 'buckeyes'],
    'Oklahoma': ['oklahoma', 'oklahoma sooners', 'ou', 'sooners'],
    'Oklahoma St.': ['oklahoma state', 'oklahoma st', 'oklahoma st.', 'osu cowboys', 'oklahoma state cowboys', 'ok state'],
    'Old Dominion': ['old dominion', 'odu', 'old dominion monarchs'],
    'Omaha': ['omaha', 'nebraska omaha', 'uno', 'omaha mavericks'],
    'Oral Roberts': ['oral roberts', 'oru', 'oral roberts golden eagles'],
    'Oregon': ['oregon', 'oregon ducks', 'uo', 'ducks'],
    'Oregon St.': ['oregon state', 'oregon st', 'oregon st.', 'osu beavers', 'oregon state beavers'],
    
    # === P ===
    'Pacific': ['pacific', 'pacific tigers', 'uop'],
    'Penn': ['penn', 'pennsylvania', 'penn quakers'],
    'Penn St.': ['penn state', 'penn st', 'penn st.', 'psu', 'penn state nittany lions', 'nittany lions'],
    'Pepperdine': ['pepperdine', 'pepperdine waves'],
    'Pittsburgh': ['pittsburgh', 'pitt', 'pitt panthers', 'pittsburgh panthers'],
    'Portland': ['portland', 'portland pilots', 'up'],
    'Portland St.': ['portland state', 'portland st', 'portland st.', 'portland state vikings'],
    'Prairie View A&M': ['prairie view', 'prairie view a&m', 'pvamu', 'prairie view a&m panthers'],
    'Presbyterian': ['presbyterian', 'presbyterian blue hose'],
    'Princeton': ['princeton', 'princeton tigers'],
    'Providence': ['providence', 'providence friars', 'friars'],
    'Purdue': ['purdue', 'purdue boilermakers', 'boilermakers'],
    'Purdue Fort Wayne': ['purdue fort wayne', 'pfw', 'fort wayne', 'ipfw'],
    
    # === Q ===
    'Queens': ['queens', 'queens royals', 'queens university'],
    'Quinnipiac': ['quinnipiac', 'quinnipiac bobcats'],
    
    # === R ===
    'Radford': ['radford', 'radford highlanders'],
    'Rhode Island': ['rhode island', 'uri', 'rhode island rams'],
    'Rice': ['rice', 'rice owls'],
    'Richmond': ['richmond', 'richmond spiders'],
    'Rider': ['rider', 'rider broncs'],
    'Robert Morris': ['robert morris', 'rmu', 'robert morris colonials'],
    'Rutgers': ['rutgers', 'rutgers scarlet knights', 'scarlet knights'],
    
    # === S ===
    'Sacramento St.': ['sacramento state', 'sacramento st', 'sacramento st.', 'sac state', 'sacramento state hornets'],
    'Sacred Heart': ['sacred heart', 'sacred heart pioneers', 'shu'],
    'Saint Louis': ['saint louis', 'st louis', 'slu', 'saint louis billikens', 'billikens'],
    "Saint Joseph's": ['saint josephs', "saint joseph's", 'st josephs', "st. joseph's", "st joseph's", 'saint josephs hawks'],
    "Saint Mary's": ["saint mary's", 'saint marys', "st mary's", 'st marys', "saint mary's gaels", 'smcgaels'],
    "Saint Peter's": ["saint peter's", 'saint peters', "st peter's", 'st peters', "saint peter's peacocks"],
    'Sam Houston St.': ['sam houston state', 'sam houston st', 'sam houston st.', 'sam houston', 'shsu', 'sam houston bearkats'],
    'Samford': ['samford', 'samford bulldogs'],
    'San Diego': ['san diego', 'san diego toreros', 'usd'],
    'San Diego St.': ['san diego state', 'san diego st', 'san diego st.', 'sdsu', 'san diego state aztecs', 'aztecs'],
    'San Francisco': ['san francisco', 'usf', 'san francisco dons', 'sf dons'],
    'San Jose St.': ['san jose state', 'san jose st', 'san jose st.', 'sjsu', 'san jose state spartans'],
    'Santa Clara': ['santa clara', 'santa clara broncos', 'scu'],
    'Seattle': ['seattle', 'seattle redhawks', 'seattle u', 'seattle university'],
    'Seton Hall': ['seton hall', 'seton hall pirates'],
    'Siena': ['siena', 'siena saints'],
    'SMU': ['smu', 'southern methodist', 'smu mustangs'],
    'South Alabama': ['south alabama', 'usa', 'south alabama jaguars'],
    'South Carolina': ['south carolina', 'south carolina gamecocks', 'usc', 'gamecocks'],
    'South Carolina St.': ['south carolina state', 'south carolina st', 'south carolina st.', 'scsu', 'south carolina state bulldogs'],
    'South Carolina Upstate': ['south carolina upstate', 'usc upstate', 'upstate'],
    'South Dakota': ['south dakota', 'usd', 'south dakota coyotes'],
    'South Dakota St.': ['south dakota state', 'south dakota st', 'south dakota st.', 'sdsu jackrabbits', 'south dakota state jackrabbits'],
    'South Florida': ['south florida', 'usf bulls', 'usf', 'south florida bulls'],
    'Southeast Missouri St.': ['southeast missouri state', 'southeast missouri st', 'semo', 'southeast missouri st.'],
    'Southeastern Louisiana': ['southeastern louisiana', 'selu', 'southeastern louisiana lions'],
    'Southern': ['southern', 'southern university', 'southern jaguars', 'subr'],
    'Southern California': ['southern california', 'usc', 'usc trojans', 'trojans', 'southern cal'],
    'Southern Illinois': ['southern illinois', 'siu', 'siu salukis', 'southern illinois salukis'],
    'Southern Indiana': ['southern indiana', 'usi', 'southern indiana screaming eagles'],
    'Southern Miss': ['southern miss', 'usm', 'southern mississippi', 'southern miss golden eagles'],
    'Southern Utah': ['southern utah', 'suu', 'southern utah thunderbirds'],
    'St. Bonaventure': ['st bonaventure', 'st. bonaventure', 'saint bonaventure', 'bonnies', 'st bonaventure bonnies'],
    'St. Francis (PA)': ['st francis pa', 'st. francis pa', 'saint francis pa', 'st francis (pa)', 'st. francis (pa)', 'red flash'],
    "St. John's": ["st john's", "st. john's", 'saint johns', "saint john's", 'st johns', "st john's red storm", 'red storm', 'johnnies'],
    'St. Thomas': ['st thomas', 'st. thomas', 'saint thomas', 'st thomas tommies', 'st thomas mn'],
    'Stanford': ['stanford', 'stanford cardinal'],
    'Stephen F. Austin': ['stephen f austin', 'stephen f. austin', 'sfa', 'stephen f austin lumberjacks'],
    'Stetson': ['stetson', 'stetson hatters'],
    'Stonehill': ['stonehill', 'stonehill skyhawks'],
    'Stony Brook': ['stony brook', 'stony brook seawolves', 'suny stony brook'],
    'Syracuse': ['syracuse', 'syracuse orange', 'cuse'],
    
    # === T ===
    'Tarleton St.': ['tarleton state', 'tarleton st', 'tarleton st.', 'tarleton', 'tarleton state texans'],
    'TCU': ['tcu', 'texas christian', 'tcu horned frogs', 'horned frogs'],
    'Temple': ['temple', 'temple owls'],
    'Tennessee': ['tennessee', 'tennessee volunteers', 'vols', 'ut'],
    'Tennessee St.': ['tennessee state', 'tennessee st', 'tennessee st.', 'tsu', 'tennessee state tigers'],
    'Tennessee Tech': ['tennessee tech', 'ttu', 'tennessee tech golden eagles'],
    'Texas': ['texas', 'texas longhorns', 'ut', 'longhorns', 'ut austin'],
    'Texas A&M': ['texas a&m', 'tamu', 'texas a&m aggies', 'aggies'],
    'Texas A&M-Commerce': ['texas a&m commerce', 'a&m commerce', 'tamuc'],
    'Texas A&M-Corpus Christi': ['texas a&m corpus christi', 'tamucc', 'a&m corpus christi', 'islanders'],
    'Texas Southern': ['texas southern', 'txso', 'texas southern tigers'],
    'Texas St.': ['texas state', 'texas st', 'texas st.', 'txst', 'texas state bobcats'],
    'Texas Tech': ['texas tech', 'ttu', 'texas tech red raiders', 'red raiders'],
    'Toledo': ['toledo', 'toledo rockets'],
    'Towson': ['towson', 'towson tigers'],
    'Troy': ['troy', 'troy trojans'],
    'Tulane': ['tulane', 'tulane green wave'],
    'Tulsa': ['tulsa', 'tulsa golden hurricane'],
    
    # === U ===
    'UAB': ['uab', 'alabama birmingham', 'uab blazers'],
    'UC Davis': ['uc davis', 'davis', 'uc davis aggies'],
    'UC Irvine': ['uc irvine', 'uci', 'uc irvine anteaters'],
    'UC Riverside': ['uc riverside', 'ucr', 'uc riverside highlanders'],
    'UC San Diego': ['uc san diego', 'ucsd', 'uc san diego tritons'],
    'UC Santa Barbara': ['uc santa barbara', 'ucsb', 'uc santa barbara gauchos'],
    'UCLA': ['ucla', 'ucla bruins'],
    'UMass Lowell': ['umass lowell', 'lowell', 'umass lowell river hawks'],
    'UMBC': ['umbc', 'maryland baltimore county', 'umbc retrievers'],
    'UMES': ['umes', 'maryland eastern shore', 'umes hawks'],
    'UNC Asheville': ['unc asheville', 'unca', 'unc asheville bulldogs'],
    'UNC Greensboro': ['unc greensboro', 'uncg', 'unc greensboro spartans'],
    'UNC Wilmington': ['unc wilmington', 'uncw', 'unc wilmington seahawks'],
    'UNLV': ['unlv', 'nevada las vegas', 'unlv rebels'],
    'USC Upstate': ['usc upstate', 'south carolina upstate'],
    'UT Arlington': ['ut arlington', 'uta', 'texas arlington', 'ut arlington mavericks', 'uta mavericks'],
    'UT Rio Grande Valley': ['ut rio grande valley', 'utrgv', 'utrgv vaqueros'],
    'Utah': ['utah', 'utah utes', 'utes'],
    'Utah St.': ['utah state', 'utah st', 'utah st.', 'usu', 'utah state aggies'],
    'Utah Tech': ['utah tech', 'dixie state', 'utah tech trailblazers'],
    'Utah Valley': ['utah valley', 'uvu', 'utah valley wolverines'],
    'UTEP': ['utep', 'texas el paso', 'utep miners'],
    'UTSA': ['utsa', 'ut san antonio', 'texas san antonio', 'utsa roadrunners'],
    
    # === V ===
    'Valparaiso': ['valparaiso', 'valpo', 'valparaiso beacons'],
    'Vanderbilt': ['vanderbilt', 'vanderbilt commodores', 'vandy'],
    'VCU': ['vcu', 'virginia commonwealth', 'vcu rams'],
    'Vermont': ['vermont', 'vermont catamounts', 'uvm'],
    'Villanova': ['villanova', 'villanova wildcats', 'nova'],
    'Virginia': ['virginia', 'virginia cavaliers', 'uva', 'wahoos', 'cavaliers'],
    'Virginia Tech': ['virginia tech', 'vt', 'virginia tech hokies', 'hokies'],
    'VMI': ['vmi', 'virginia military', 'vmi keydets'],
    
    # === W ===
    'Wagner': ['wagner', 'wagner seahawks'],
    'Wake Forest': ['wake forest', 'wake forest demon deacons', 'wake', 'demon deacons'],
    'Washington': ['washington', 'washington huskies', 'uw', 'huskies'],
    'Washington St.': ['washington state', 'washington st', 'washington st.', 'wsu', 'washington state cougars', 'wazzu'],
    'Weber St.': ['weber state', 'weber st', 'weber st.', 'weber state wildcats'],
    'West Virginia': ['west virginia', 'wvu', 'west virginia mountaineers', 'mountaineers'],
    'Western Carolina': ['western carolina', 'wcu', 'western carolina catamounts'],
    'Western Illinois': ['western illinois', 'wiu', 'western illinois leathernecks'],
    'Western Kentucky': ['western kentucky', 'wku', 'western kentucky hilltoppers'],
    'Western Michigan': ['western michigan', 'wmu', 'western michigan broncos'],
    'Wichita St.': ['wichita state', 'wichita st', 'wichita st.', 'wichita state shockers', 'shockers'],
    'William & Mary': ['william & mary', 'william and mary', 'w&m', 'william & mary tribe'],
    'Winthrop': ['winthrop', 'winthrop eagles'],
    'Wisconsin': ['wisconsin', 'wisconsin badgers', 'badgers'],
    'Wofford': ['wofford', 'wofford terriers'],
    'Wright St.': ['wright state', 'wright st', 'wright st.', 'wright state raiders'],
    'Wyoming': ['wyoming', 'wyoming cowboys'],
    
    # === X ===
    'Xavier': ['xavier', 'xavier musketeers', 'musketeers'],
    
    # === Y ===
    'Yale': ['yale', 'yale bulldogs'],
    'Youngstown St.': ['youngstown state', 'youngstown st', 'youngstown st.', 'ysu', 'youngstown state penguins'],
}


def build_lookup_table():
    """Build a reverse lookup table from all variations to canonical names."""
    lookup = {}
    for canonical, variations in TEAM_DATABASE.items():
        # Add canonical name itself
        lookup[canonical.lower()] = canonical
        # Add all variations
        for var in variations:
            lookup[var.lower()] = canonical
    return lookup


# Pre-built lookup table
TEAM_LOOKUP = build_lookup_table()


def normalize_team_name(name: str) -> str:
    """
    Normalize a team name to its canonical form.
    
    Args:
        name: Any team name variation (e.g., "Idaho State Bengals")
        
    Returns:
        Canonical team name (e.g., "Idaho St.")
    """
    if not name:
        return None
    
    clean = name.lower().strip()
    
    # Direct lookup
    if clean in TEAM_LOOKUP:
        return TEAM_LOOKUP[clean]
    
    # Try removing common suffixes and look again
    suffixes = ['wildcats', 'bulldogs', 'tigers', 'bears', 'eagles', 'hawks',
                'cardinals', 'panthers', 'lions', 'knights', 'warriors',
                'cougars', 'huskies', 'hornets', 'owls', 'rams', 'rebels',
                'blue devils', 'tar heels', 'spartans', 'wolverines',
                'volunteers', 'gators', 'seminoles', 'hurricanes', 'aggies',
                'cowboys', 'sooners', 'jayhawks', 'cyclones', 'buckeyes',
                'hoosiers', 'badgers', 'hawkeyes', 'terrapins', 'nittany lions',
                'orange', 'ducks', 'beavers', 'golden bears', 'bruins',
                'trojans', 'sun devils', 'buffaloes', 'utes', 'lobos',
                'aztecs', 'falcons', 'broncos', 'mountaineers', 'red raiders',
                'longhorns', 'razorbacks', 'gamecocks', 'commodores',
                'crimson tide', 'fighting irish', 'hoyas', 'blue jays',
                'musketeers', 'explorers', 'billikens', 'flyers', 'dukes',
                'gaels', 'friars', 'red storm', 'pirates', 'golden eagles',
                'shockers', 'bluejays', 'demon deacons', 'hokies', 'cavaliers',
                'yellow jackets', 'fighting illini', 'boilermakers', 'scarlet knights']
    
    clean_no_suffix = clean
    for suffix in suffixes:
        if clean.endswith(suffix):
            clean_no_suffix = clean[:-len(suffix)].strip()
            break
    
    if clean_no_suffix in TEAM_LOOKUP:
        return TEAM_LOOKUP[clean_no_suffix]
    
    # Try word-by-word matching for partial matches
    # This helps with "Georgia St Panthers" -> "Georgia St."
    words = clean.split()
    for i in range(len(words), 0, -1):
        partial = ' '.join(words[:i])
        if partial in TEAM_LOOKUP:
            return TEAM_LOOKUP[partial]
    
    # Last resort: return None (not found)
    return None


def get_all_team_names():
    """Return list of all canonical team names."""
    return list(TEAM_DATABASE.keys())


if __name__ == "__main__":
    # Test the matcher
    test_cases = [
        "Idaho State Bengals",
        "Idaho State",
        "Idaho",
        "Idaho Vandals",
        "Florida Atlantic Owls",
        "Florida Atlantic",
        "Florida",
        "Florida Gators",
        "George Mason Patriots",
        "George Mason",
        "George Washington",
        "Georgetown Hoyas",
        "Georgia Bulldogs",
        "Georgia Tech Yellow Jackets",
        "Georgia State Panthers",
        "Texas State Bobcats",
        "Texas Longhorns",
        "Texas Tech Red Raiders",
        "Missouri State Bears",
        "Missouri Tigers",
        "Ohio State Buckeyes",
        "Ohio Bobcats",
        "Michigan Wolverines",
        "Michigan State Spartans",
        "Utah Utes",
        "Utah State Aggies",
        "Northern Iowa Panthers",
        "UNI",
    ]
    
    print("Team Name Matching Tests")
    print("=" * 60)
    for test in test_cases:
        result = normalize_team_name(test)
        status = "✅" if result else "❌"
        print(f"{status} '{test}' -> '{result}'")