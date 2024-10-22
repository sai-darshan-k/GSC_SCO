from flask import Flask, request, jsonify, render_template
import json
import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup

app = Flask(__name__)

# Load your API key from config.json
with open('config.json') as config_file:
    config = json.load(config_file)

API_KEY = config['API_KEY']

# Fetch author papers from Scopus using author ID
def fetch_author_papers(author_id):
    url = f'https://api.elsevier.com/content/search/scopus?query=AU-ID({author_id})'
    
    headers = {
        'X-ELS-APIKey': API_KEY,
        'Accept': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Unable to fetch data for author ID {author_id}. Status code: {response.status_code}")
        return None

# Parse Scopus data
def parse_scopus_data(response_json):
    total_papers = 0
    total_citations = 0
    h_index = 0
    
    if response_json and 'search-results' in response_json:
        entries = response_json['search-results'].get('entry', [])
        total_papers = len(entries)
        
        citations = [int(entry.get('citedby-count', '0')) for entry in entries]
        total_citations = sum(citations)
        
        # Calculate H-index
        citations.sort(reverse=True)
        h_index = sum(c >= i + 1 for i, c in enumerate(citations))
    
    return total_papers, total_citations, h_index

def fetch_author_papers(author_id):
    url = f'https://api.elsevier.com/content/search/scopus?query=AU-ID({author_id})'
    
    headers = {
        'X-ELS-APIKey': API_KEY,
        'Accept': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Unable to fetch data for author ID {author_id}. Status code: {response.status_code}")
        return None

def parse_scopus_papers(response_json):
    papers = []
    if response_json and 'search-results' in response_json:
        entries = response_json['search-results'].get('entry', [])
        for entry in entries:
            paper = {
                'title': entry.get('dc:title'),
                'year': entry.get('prism:coverDate', '')[:4], 
                'citations': entry.get('citedby-count'),
                'link': entry.get('prism:doi')
            }
            papers.append(paper)
    return papers

def fetch_google_scholar_data(gscholar_link):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(gscholar_link, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        try:
            publication_entries = soup.find_all('tr', class_='gsc_a_tr')
            total_papers = len(publication_entries)

            citation_count = soup.find('td', class_='gsc_rsb_std')
            total_citations = int(citation_count.text.strip()) if citation_count else 0
            
            # Find the statistics table
            stats = soup.find_all('td', class_='gsc_rsb_std')

            h_index = 0
            i10_index = 0

            # Ensure we have enough statistics cells
            if len(stats) >= 5:
                h_index = int(stats[2].text.strip()) if stats[2] else 0
                i10_index = int(stats[4].text.strip()) if stats[4] else 0

            return total_papers, total_citations, h_index, i10_index
        except (IndexError, ValueError) as e:
            print(f"Error parsing Google Scholar data for {gscholar_link}: {e}")
            return None, None, None, None
    else:
        print(f"Error fetching Google Scholar data from {gscholar_link}: Status code {response.status_code}")
        return None, None, None, None

def fetch_yearly_citations(gscholar_link):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(gscholar_link, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        try:
            yearly_data = {}
            
            # Find all the year elements
            year_elements = soup.find_all('span', class_='gsc_g_t')
            # Find all the citation count elements
            citation_elements = soup.find_all('span', class_='gsc_g_al')

            # Iterate over the years and corresponding citations
            for year_elem, citation_elem in zip(year_elements, citation_elements):
                year = year_elem.text.strip()
                citation_count = citation_elem.text.strip()

                # Clean the citation count and convert to int
                citation_count = int(citation_count) if citation_count.isdigit() else 0
                yearly_data[year] = citation_count

            return yearly_data
        
        except Exception as e:
            print(f"Error fetching yearly citations: {e}")
            return {}

    else:
        print(f"Error fetching Google Scholar data from {gscholar_link}: Status code {response.status_code}")
        return {}

def fetch_google_scholar_papers(gscholar_link):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(gscholar_link, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        papers = []

        publication_entries = soup.find_all('tr', class_='gsc_a_tr')
        for entry in publication_entries:
            title = entry.find('a', class_='gsc_a_at').text
            citation_count = entry.find('td', class_='gsc_a_c').text.strip()  # Citation count
            year = entry.find('span', class_='gsc_a_h gsc_a_hc').text.strip()  # Year of publication

            # Collect details
            papers.append({
                'title': title,
                'citations': citation_count,
                'year': year,
                'link': 'https://scholar.google.com' + entry.find('a', class_='gsc_a_at')['data-href']  # Link to paper
            })
        return papers
    else:
        print(f"Error fetching papers from {gscholar_link}: Status code {response.status_code}")
        return []
    
def fetch_google_scholar_papers(author_url):
    papers = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(author_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if 'Our systems have detected unusual traffic' in soup.text:
            print(f"CAPTCHA detected for {author_url}. Unable to fetch papers.")
            return papers

        entries = soup.find_all('tr', class_='gsc_a_tr')
        
        if not entries:
            print(f"No paper entries found for {author_url}. The page structure might have changed.")
            return papers

        for entry in entries:
            title_element = entry.find('a', class_='gsc_a_at')
            citations_element = entry.find('a', class_='gsc_a_ac gs_ibl')
            year_element = entry.find('span', class_='gsc_a_h gsc_a_hc gs_ibl')
            
            title = title_element.text.strip() if title_element else 'N/A'
            link = f"https://scholar.google.com{title_element['href']}" if title_element and 'href' in title_element.attrs else 'N/A'
            citations = citations_element.text.strip() if citations_element else '0'
            year = year_element.text.strip() if year_element else 'N/A'
            
            # If year is empty, set it to 'N/A'
            if year == '':
                year = 'N/A'
            
            papers.append({
                'title': title,
                'link': link,
                'citations': citations,
                'year': year
            })
        
        if not papers:
            print(f"No papers could be extracted from {author_url}. The page structure might have changed.")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching papers for {author_url}: {str(e)}")
    except Exception as e:
        print(f"Unexpected error while processing {author_url}: {str(e)}")
    
    return papers


@app.route('/')
def index():
    return render_template('index.html')
@app.route('/generate_report', methods=['POST'])
def generate_report():
    data = request.json
    source = data.get('source')

    # List of authors with Scopus IDs and Google Scholar links
    author_ids = [
        ("57223100630", "Dr AMRUTHA", "https://scholar.google.com/citations?user=fzs9d1IAAAAJ&hl=en"),
        ("55079543700", "Dr ANITA H B", "https://scholar.google.com/citations?user=-ZYIiGAAAAAJ&hl=en"),
        ("35737586100", "Dr AROKIA PAUL RAJAN R", "https://scholar.google.com/citations?hl=en&user=5Dl7tEYAAAAJ"),
        ("57189239708", "Dr ASHOK IMMANUEL V", "https://scholar.google.co.in/citations?user=px8Z3Q4AAAAJ&hl=en"),
        ("55881946700", "Dr BEAULAH SOUNDARABAI P", "https://scholar.google.co.in/citations?user=jTCHV4kAAAAJ&hl=en"),
        ("57044254900", "Dr CECIL DONALD A", "https://scholar.google.co.in/citations?user=_bbxYHsAAAAJ&hl=en&authuser=1"),
        ("57055221400", "Dr CHANDRA J", "https://scholar.google.com/citations?user=bn6WQUoAAAAJ"),
        ("59256484700", "Dr CYNTHIA T", "https://scholar.google.com/citations?hl=en&user=ThELNO0AAAAJ"),
        ("57162822500", "Dr DEEPA V JOSE", "https://scholar.google.co.in/citations?user=ryhyx4IAAAAJ&hl=en"),
        ("57205027677", "FABIOLA HAZEL POHRMEN", "https://scholar.google.com/citations?user=prcv4fAAAAAJ&hl=en&oi=ao")
    ]
    # Handle fetching Google Scholar paper details
    if source == 'paperDetails':
        paper_details = []
        for author_id, author_name, gscholar_link in author_ids:
            papers = fetch_google_scholar_papers(gscholar_link)
            print(f"Google Scholar Papers for {author_name}: {papers}")  # Debug logging
            paper_details.append({'Name': author_name, 'Papers': papers})
        return jsonify(paper_details)

    # Handle fetching Scopus paper details
    elif source == 'paperDetailsScopus':
        all_authors_data = []
        for author_id, author_name, _ in author_ids:
            scopus_response_json = fetch_author_papers(author_id)
            papers = parse_scopus_papers(scopus_response_json)
            author_data = {
                "Name": author_name,
                "ScopusPapers": papers,
                "ProfileLink": f"https://www.scopus.com/authid/detail.uri?authorId={author_id}"
            }
            all_authors_data.append(author_data)
        return jsonify(all_authors_data)

    # Handle 'both' option if needed (existing functionality)
    elif source == 'both':
        # Your existing code for 'both' option here
        pass

    # Handle 'average' option if needed (existing functionality)
    elif source == 'average':
        # Your existing code for 'average' option here
        pass

    # Handle 'googleScholarOnly' option if needed (existing functionality)
    elif source == 'googleScholarOnly':
        # Your existing code for 'googleScholarOnly' option here
        pass

    else:
        return jsonify({"error": "Invalid source specified"}), 400

    # Logic for handling 'both' and 'average' options (existing code) remains here...

    combined_data = []

    # Fetch data for each author
    for author_id, author_name, gscholar_link in author_ids:
        scopus_response_json = fetch_author_papers(author_id)
        total_papers_scopus, total_citations_scopus, h_index_scopus = parse_scopus_data(scopus_response_json)
        total_papers_gscholar, total_citations_gscholar, h_index_gscholar, i10_index = fetch_google_scholar_data(gscholar_link)

        # Get yearly citations
        yearly_citations = fetch_yearly_citations(gscholar_link)

        # Convert yearly_citations dictionary to a string format for easy display
        yearly_citations_str = ', '.join(f"{year}: {count}" for year, count in yearly_citations.items())

        # Append individual author data
        combined_data.append({
            'Name': author_name,
            'Total Papers (Google Scholar)': total_papers_gscholar or 0,
            'Total Citations (Google Scholar)': total_citations_gscholar or 0,
            'H-Index (Google Scholar)': h_index_gscholar or 0,
            'I10 Index (Google Scholar)': i10_index or 0,
            'Total Papers (Scopus)': total_papers_scopus or 0,
            'Total Citations (Scopus)': total_citations_scopus or 0,
            'H-Index (Scopus)': h_index_scopus or 0,
            'Yearly Citations': yearly_citations_str  # Store as a formatted string
        })

    # Handle "googleScholarOnly" source
    if source == 'googleScholarOnly':
        google_scholar_data = []
        for entry in combined_data:
            google_scholar_data.append({
                'Name': entry['Name'],
                'Total Citations': entry['Total Citations (Google Scholar)'],
                'H-Index': entry['H-Index (Google Scholar)'],
                'I10 Index': entry['I10 Index (Google Scholar)'],
                'Yearly Citations': entry['Yearly Citations']
            })
        return jsonify(google_scholar_data)

    # If source is "average", calculate individual averages per author
    if source == 'average':
        avg_data = []

        for entry in combined_data:
            avg_data.append({
                'Name': entry['Name'],
                'Total Papers (Google Scholar)': entry['Total Papers (Google Scholar)'],
                'Total Citations (Google Scholar)': entry['Total Citations (Google Scholar)'],
                'H-Index (Google Scholar)': entry['H-Index (Google Scholar)'],
                'I10 Index (Google Scholar)': entry['I10 Index (Google Scholar)'],
                'Total Papers (Scopus)': entry['Total Papers (Scopus)'],
                'Total Citations (Scopus)': entry['Total Citations (Scopus)'],
                'H-Index (Scopus)': entry['H-Index (Scopus)'],
                'Yearly Citations': entry['Yearly Citations'],
            })

        return jsonify(avg_data)

    # Filter data based on the source requested (if not 'average')
    filtered_data = []
    for entry in combined_data:
        filtered_entry = {'Name': entry['Name']}
        if source == 'googleScholar' or source == 'both':
            filtered_entry['Total Papers (Google Scholar)'] = entry['Total Papers (Google Scholar)']
            filtered_entry['Total Citations (Google Scholar)'] = entry['Total Citations (Google Scholar)']
            filtered_entry['H-Index (Google Scholar)'] = entry['H-Index (Google Scholar)']
            filtered_entry['I10 Index (Google Scholar)'] = entry['I10 Index (Google Scholar)']
            filtered_entry['Yearly Citations'] = entry['Yearly Citations']
        if source == 'scopus' or source == 'both':
            filtered_entry['Total Papers (Scopus)'] = entry['Total Papers (Scopus)']
            filtered_entry['Total Citations (Scopus)'] = entry['Total Citations (Scopus)']
            filtered_entry['H-Index (Scopus)'] = entry['H-Index (Scopus)']

        filtered_data.append(filtered_entry)


    return jsonify(filtered_data)

if __name__ == '__main__':
    app.run(debug=True)